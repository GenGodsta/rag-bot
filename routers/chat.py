from fastapi import WebSocket, WebSocketDisconnect, APIRouter, Depends
from mcp_instance import mcp_client
from mongo import connect_db
from milvus_crossencoding import retrieve, rerank_chunks
from ollama import AsyncClient
from authorization import decode_token
from history import save_chat, get_history_collection, get_memory_collection, get_context_for_query, update_memory
from mongo_store import MongoStore
import json
import asyncio
import re

router = APIRouter()

_store = None

def get_store():
    global _store
    if _store is None:
        from app import app
        _store = MongoStore(app.state.mongo["ragdb"]["user_facts"])
    return _store


tools = [
    {
        "type": "function",
        "function": {
            "name": "web_research",
            "description": "Search the web (Google + Wikipedia) for information not found in the ML textbooks. Use this when the question is about current events, people, or topics unrelated to machine learning.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"}
                },
                "required": ["query"]
            }
        }
    }
]


# ---------------------------------------------------------------------------
# Change 1: gating / classification
# ---------------------------------------------------------------------------
async def classify_query(query: str) -> bool:
    """
    Cheap, fast pre-check: is this question plausibly answerable from the
    ML/AI textbook corpus, or is it clearly something else (current events,
    people, general trivia, unrelated domains)?

    Returns True  -> try the book corpus (Milvus retrieval)
            False -> skip retrieval entirely, go straight to web search
    """
    prompt = f"""Classify this question as BOOK or WEB.

BOOK = the question is about AI/ML concepts, algorithms, theory, models, statistics,
or anything that would plausibly be covered in machine learning textbooks.
WEB = the question is about current events, specific people, news, dates, or any
topic clearly outside ML/AI textbook content.

Respond with exactly one word: BOOK or WEB. No explanation.

QUESTION: {query}"""

    try:
        response = await AsyncClient().chat(
            model="llama3.1:8b",
            messages=[{"role": "user", "content": prompt}],
            options={"num_ctx": 256}
        )
        answer = response.message.content.strip().upper()
        return "WEB" not in answer
    except Exception as e:
        print(f"[classify_query] failed, defaulting to BOOK: {e}")
        return True


async def mcp_web_search(query: str, topk: int = 15) -> list:
    print(f"[mcp_web_search] Sending to Serper/Wikipedia via MCP: {query!r} (topk={topk})")
    try:
        raw_result = await mcp_client.call_tool("web_research", {"query": query, "num_results": topk})
        if not raw_result:
            print(f"[mcp_web_search] Empty raw_result for query: {query!r}")
            return []
        parsed = json.loads(raw_result[0].text)
        print(f"[mcp_web_search] Got {len(parsed) if isinstance(parsed, list) else 1} results for: {query!r}")
        if isinstance(parsed, dict):
            parsed = [parsed]
        return [
            {"text": item.get("snippet", ""), "source": item.get("url", ""),
             "page": "Web", "score": 0.0, "from_web": True}
            for item in parsed
        ]
    except Exception as e:
        print(f"MCP web search failed for query {query!r}: {e}")
        return []


async def recall_long_term_facts(user_id: str, query: str, store: MongoStore) -> str:
    items = await store.asearch(("user_facts", user_id), query=query)
    if not items:
        return ""
    facts = "\n".join(f"- {item.value['fact']}" for item in items)
    return f"WHAT YOU KNOW ABOUT THIS USER (long-term):\n{facts}"


async def update_long_term_facts(user_id: str, query: str, answer: str, store: MongoStore):
    prompt = f"""Extract durable facts about the USER (background, preferences, goals) from this exchange.
Skip anything only relevant to this single question.

Respond with ONLY a JSON array. Every item must be exactly {{"fact": "<text>"}}. No other keys. No markdown, no explanation, no text before or after the array.

Example output: [{{"fact": "user is vegetarian"}}, {{"fact": "user weighs 80kg"}}]

If there are no durable facts, respond with exactly: []

User: {query}
Assistant: {answer}"""

    try:
        response = await AsyncClient().chat(
            model="llama3.1:8b",
            messages=[{"role": "user", "content": prompt}],
            options={"num_ctx": 4096}
        )
        raw = response.message.content.strip()
        print(f"[fact_extraction] raw response: {raw!r}")

        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if not match:
            raise ValueError("No JSON array found in response")
        facts = json.loads(match.group(0))
        facts = [f for f in facts if isinstance(f, dict) and "fact" in f]
    except Exception as e:
        print(f"Long-term fact extraction failed: {e}")
        facts = []

    for f in facts:
        key = f"fact_{abs(hash(f['fact'])) % 100000}"
        await store.aput(("user_facts", user_id), key, {"fact": f["fact"]})


# ---------------------------------------------------------------------------
# Change 2: dedup / synthesis instructions baked into the prompts
# ---------------------------------------------------------------------------
DEDUP_INSTRUCTIONS = """When multiple excerpts/sources say the same thing, synthesize them into a single unified
statement instead of repeating it per source (avoid patterns like "Source A says X. Source B also says X.").
Only attribute a point to a specific source when sources genuinely disagree, add distinct detail, or when the
user asked where something comes from. Cite sources compactly (e.g. grouped at the end of a point) rather than
narrating each source in turn."""


def build_prompt(query: str, context: str, conversation_context: str = "") -> str:
    conv_block = (
        f"PREVIOUS CONVERSATION (for reference only — do NOT treat this as book excerpts):\n{conversation_context}\n"
        if conversation_context else ""
    )
    return f"""You are a helpful AI assistant answering questions from AI/ML books.
You have been given relevant excerpts from the books. Use them to answer the question thoroughly.
Only say "I don't have enough information" if the excerpts are completely unrelated to the question.
If the excerpts contain partial information, use it to give the best answer you can.
Always mention which book and page your answer comes from.
Do not treat the previous conversation as a source of factual grounding — only the CONTEXT section below counts as evidence from the books.
{DEDUP_INSTRUCTIONS}

{conv_block}
CONTEXT:
{context}

QUESTION: {query}

ANSWER:"""

def build_web_prompt(query: str, context: str, conversation_context: str = "") -> str:
    conv_block = (
        f"PREVIOUS CONVERSATION (for reference only — do NOT treat this as search results):\n{conversation_context}\n"
        if conversation_context else ""
    )
    return f"""You are a helpful AI assistant. Answer the question using only the web search results provided below.
Do not use your own knowledge. If the results don't contain enough information, say so.
Do not treat the previous conversation as a source of factual grounding — only the WEB SEARCH RESULTS section counts as evidence.
{DEDUP_INSTRUCTIONS}

{conv_block}
WEB SEARCH RESULTS:
{context}

QUESTION: {query}

ANSWER:"""

def build_context(chunks: list) -> str:
    context = ""
    for i, chunk in enumerate(chunks):
        source = chunk.get("source", "Web")
        page = chunk.get("page", "Web")
        context += f"\n[Source {i+1}: {source} | Page {page}]\n"
        context += chunk['text'] + "\n"
    return context


def build_sources(chunks: list) -> list:
    return [
        {
            "source": chunk.get("source", "Web Search").replace(".pdf", ""),
            "page": chunk.get("page", "Web"),
            "score": round(chunk.get("score", 0.0), 2),
            "preview": chunk["text"][:150] + "..."
        }
        for chunk in chunks
    ]


def build_conversation_context(memory: dict) -> str:
    parts = []
    if memory.get("summary"):
        parts.append(f"CONVERSATION SUMMARY (earlier context):\n{memory['summary']}")
    recent = memory.get("recent_turns", [])
    if recent:
        turns_text = "\n".join(f"User: {t['query']}\nAssistant: {t['answer']}" for t in recent)
        parts.append(f"RECENT CONVERSATION:\n{turns_text}")
    return "\n\n".join(parts) if parts else ""


async def run_web_branch(query: str, conversation_context: str, user_id: str) -> list:
    """Shared web-search path used both for gated-out queries and low-score fallback."""
    tool_call_prompt = f"""{conversation_context}

Based on the conversation above, generate a precise web search query for the user's current question.
Resolve any pronouns or vague references (like "it", "that", "the stations") using the conversation context.

CURRENT QUESTION: {query}"""

    response = await AsyncClient().chat(
        model="llama3.1:8b",
        messages=[{"role": "user", "content": tool_call_prompt}],
        tools=tools,
        options={"num_ctx": 4096}
    )
    if response.message.tool_calls:
        tool_call = response.message.tool_calls[0]
        search_query = tool_call.function.arguments["query"]
        print(f"[user:{user_id}] LLM chose tool_call search_query: {search_query!r}")
        chunks = await mcp_web_search(search_query, topk=15)
    else:
        print(f"[user:{user_id}] No tool call returned, falling back to raw query: {query!r}")
        chunks = await mcp_web_search(query, topk=15)

    chunks = await rerank_chunks(query, chunks, top_k=5)
    if chunks:
        print(f"[Web Search] Top score: {chunks[0]['score']:.2f}")
    return chunks


@router.websocket("/ws/chat")
async def websocket_chat(
    websocket: WebSocket,
    token: str,
    dbcollection=Depends(connect_db),
    history_col=Depends(get_history_collection),
    memory_col=Depends(get_memory_collection)
):
    user_id = decode_token(token)
    store = get_store()

    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            query = data["query"]
            topk = data.get("topk", 5)

            short_term, long_term_text, is_book_query = await asyncio.gather(
                get_context_for_query(user_id, memory_col),
                recall_long_term_facts(user_id, query, store),
                classify_query(query),
            )
            conversation_context = long_term_text + "\n\n" + build_conversation_context(short_term)

            from_web = False

            if is_book_query:
                chunks = await retrieve(query, topk, dbcollection)
                top_score = chunks[0]["score"] if chunks else 0.0

                if not chunks or top_score < 3.0:
                    print(f"[user:{user_id}] Low/no relevance ({top_score:.2f}) — invoking web_search")
                    chunks = await run_web_branch(query, conversation_context, user_id)
                    from_web = True
            else:
                # Change 1: gated out of the book corpus entirely — skip Milvus/rerank,
                # go straight to web search instead of retrieving-then-discarding.
                print(f"[user:{user_id}] Gated as non-book query — skipping retrieval, going straight to web_search")
                chunks = await run_web_branch(query, conversation_context, user_id)
                from_web = True

            if not chunks:
                await websocket.send_text("I don't have enough information to answer that.")
                await websocket.send_text("__DONE__:" + json.dumps({"done": True, "sources": []}))
                continue

            context = build_context(chunks)
            prompt = (
                build_web_prompt(query, context, conversation_context)
                if from_web
                else build_prompt(query, context, conversation_context)
            )
            sources = build_sources(chunks)

            full_answer = ""
            async for chunk in await AsyncClient().chat(
                model="llama3.1:8b",
                messages=[{"role": "user", "content": prompt}],
                stream=True,
                options={"num_ctx": 4096}
            ):
                token_text = chunk.message.content
                if token_text:
                    full_answer += token_text
                    await websocket.send_text(token_text)

            await websocket.send_text("__DONE__:" + json.dumps({"done": True, "sources": sources}))

            await save_chat(user_id, query, full_answer, sources, history_col)

            asyncio.create_task(update_memory(user_id, query, full_answer, memory_col))
            asyncio.create_task(update_long_term_facts(user_id, query, full_answer, store))

    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_text("__DONE__:" + json.dumps({"error": str(e)}))
        await websocket.close()