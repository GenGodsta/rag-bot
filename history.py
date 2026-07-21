from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorCollection
from datetime import datetime
import httpx
from authorization import get_current_user

router = APIRouter(prefix="/history", tags=["history"])

MAX_RECENT_TURNS = 5  
OLLAMA_URL = "http://localhost:11434/api/chat"
SUMMARY_MODEL = "llama3.1:8b"  


async def get_history_collection() -> AsyncIOMotorCollection:
    from app import app
    return app.state.mongo["ragdb"]["chat_history"]


async def get_memory_collection() -> AsyncIOMotorCollection:
    from app import app
    return app.state.mongo["ragdb"]["chat_memory"]


async def save_chat(
    user_id: str,
    session_id: str,
    query: str,
    answer: str,
    sources: list,
    history_col: AsyncIOMotorCollection
):
    await history_col.insert_one({
        "user_id": user_id,
        "session_id": session_id,
        "query": query,
        "answer": answer,
        "sources": sources,
        "timestamp": datetime.utcnow()
    })


async def _summarize_with_llm(existing_summary: str, evicted_text: str) -> str:
    prompt = f"""You are maintaining a running summary of a conversation for context purposes.

Existing summary so far:
{existing_summary or "(none yet)"}

New exchange to incorporate:
{evicted_text}

Update the summary to concisely incorporate this new exchange, preserving important facts, entities, and user intent. Keep it compact. Output ONLY the updated summary, nothing else."""

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            OLLAMA_URL,
            json={
                "model": SUMMARY_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {"num_ctx": 4096}
            }
        )
        resp.raise_for_status()
        data = resp.json()
        return data["message"]["content"].strip()


async def update_memory(
    user_id: str,
    query: str,
    answer: str,
    memory_col: AsyncIOMotorCollection
):
  
    doc = await memory_col.find_one({"user_id": user_id})
    if doc is None:
        doc = {"user_id": user_id, "summary": "", "recent_turns": []}

    recent = doc.get("recent_turns", [])
    recent.append({"query": query, "answer": answer, "timestamp": datetime.utcnow()})

    if len(recent) > MAX_RECENT_TURNS:
        evicted = recent[: len(recent) - MAX_RECENT_TURNS]
        recent = recent[len(recent) - MAX_RECENT_TURNS:]

        evicted_text = "\n".join(
            f"User: {t['query']}\nAssistant: {t['answer']}" for t in evicted
        )
        new_summary = await _summarize_with_llm(doc.get("summary", ""), evicted_text)

        await memory_col.update_one(
            {"user_id": user_id},
            {"$set": {"summary": new_summary, "recent_turns": recent}},
            upsert=True
        )
    else:
        await memory_col.update_one(
            {"user_id": user_id},
            {"$set": {"recent_turns": recent}},
            upsert=True
        )


async def get_context_for_query(
    user_id: str,
    memory_col: AsyncIOMotorCollection
) -> dict:
    doc = await memory_col.find_one({"user_id": user_id}, {"_id": 0})
    if doc is None:
        return {"summary": "", "recent_turns": []}
    return {
        "summary": doc.get("summary", ""),
        "recent_turns": doc.get("recent_turns", [])
    }


@router.get("/")
async def get_history(
    user_id: str = Depends(get_current_user),
    limit: int = Query(default=20, le=100),
    history_col=Depends(get_history_collection)
):
    cursor = history_col.find(
        {"user_id": user_id},
        {"_id": 0}
    ).sort("timestamp", -1).limit(limit)

    records = await cursor.to_list(length=limit)
    return {"history": records}


@router.delete("/")
async def clear_history(
    user_id: str = Depends(get_current_user),
    history_col=Depends(get_history_collection),
    memory_col=Depends(get_memory_collection)
):
    result = await history_col.delete_many({"user_id": user_id})
    await memory_col.delete_one({"user_id": user_id})
    return {"deleted": result.deleted_count}

@router.get("/{session_id}")
async def get_session_history(
    session_id: str,
    user_id: str = Depends(get_current_user),
    history_col=Depends(get_history_collection)
):
    cursor = history_col.find(
        {"user_id": user_id, "session_id": session_id},
        {"_id": 0}
    ).sort("timestamp", 1)  

    records = await cursor.to_list(length=None)
    if not records:
        return {"session_id": session_id, "turns": []}
    return {"session_id": session_id, "turns": records}