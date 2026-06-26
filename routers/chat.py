from fastapi import WebSocket, WebSocketDisconnect, APIRouter, Depends
from model import chatrequest, chatresponse
from mongo import connect_db
from milvus_crossencoding import retrieve
from ollama import AsyncClient
from authorization import decode_token
from history import save_chat, get_history_collection
import json
import asyncio
from ddgs import DDGS

router = APIRouter()

tools = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for information not found in the ML textbooks. Use this when the question is about current events, people, or topics unrelated to machine learning.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query"
                    }
                },
                "required": ["query"]
            }
        }
    }
]


def build_prompt(query: str, context: str) -> str:
    return f"""You are a helpful AI assistant answering questions from AI/ML books.
You have been given relevant excerpts from the books. Use them to answer the question thoroughly.
Only say "I don't have enough information" if the excerpts are completely unrelated to the question.
If the excerpts contain partial information, use it to give the best answer you can.
Always mention which book and page your answer comes from.

CONTEXT:
{context}

QUESTION: {query}

ANSWER:"""


def build_web_prompt(query: str, context: str) -> str:
    return f"""You are a helpful AI assistant. Answer the question using only the web search results provided below.
Do not use your own knowledge. If the results don't contain enough information, say so.

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


def duck_search(query: str) -> list:
    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=5))
    return [
        {
            "text": r.get("body", ""),
            "source": r.get("href", ""),
            "page": "Web",
            "score": 0.0,
            "from_web": True
        }
        for r in results
    ]


@router.websocket("/ws/chat")
async def websocket_chat(
    websocket: WebSocket,
    token: str,                          
    dbcollection=Depends(connect_db),
    history_col=Depends(get_history_collection)
):
    user_id = decode_token(token)       

    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            query = data["query"]
            topk = data.get("topk", 5)

            chunks = await retrieve(query, topk, dbcollection)

            if not chunks:
                await websocket.send_text("I don't have enough information in the books to answer that.")
                await websocket.send_text("__DONE__:" + json.dumps({"done": True, "sources": []}))
                continue

            top_score = chunks[0]["score"]
            from_web = False

            if top_score < 3.0:
                print(f"[user:{user_id}] Low relevance ({top_score:.2f}) — invoking web_search")
                response = await AsyncClient().chat(
                    model="llama3.1:8b",
                    messages=[{"role": "user", "content": query}],
                    tools=tools
                )

                if response.message.tool_calls:
                    tool_call = response.message.tool_calls[0]
                    search_query = tool_call.function.arguments["query"]
                    chunks = await asyncio.to_thread(duck_search, search_query)
                    from_web = True
                else:
                    chunks = await asyncio.to_thread(duck_search, query)
                    from_web = True

            context = build_context(chunks)
            prompt = build_web_prompt(query, context) if from_web else build_prompt(query, context)
            sources = build_sources(chunks)

            full_answer = ""
            async for chunk in await AsyncClient().chat(
                model="llama3.1:8b",
                messages=[{"role": "user", "content": prompt}],
                stream=True
            ):
                token_text = chunk.message.content
                if token_text:
                    full_answer += token_text
                    await websocket.send_text(token_text)

            await websocket.send_text("__DONE__:" + json.dumps({"done": True, "sources": sources}))

            await save_chat(user_id, query, full_answer, sources, history_col)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_text("__DONE__:" + json.dumps({"error": str(e)}))
        await websocket.close()