from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorCollection
from datetime import datetime
from authorization import get_current_user

router = APIRouter(prefix="/history", tags=["history"])


async def get_history_collection() -> AsyncIOMotorCollection:
    from app import app
    return app.state.mongo["ragdb"]["chat_history"]


async def save_chat(
    user_id: str,
    query: str,
    answer: str,
    sources: list,
    history_col: AsyncIOMotorCollection
):
    """Called internally from chat.py after each response."""
    await history_col.insert_one({
        "user_id": user_id,
        "query": query,
        "answer": answer,
        "sources": sources,
        "timestamp": datetime.utcnow()
    })


@router.get("/")
async def get_history(
    user_id: str = Depends(get_current_user),
    limit: int = Query(default=20, le=100),
    history_col=Depends(get_history_collection)
):
    """Fetch the most recent `limit` Q&A pairs for the logged-in user."""
    cursor = history_col.find(
        {"user_id": user_id},
        {"_id": 0}  # exclude mongo _id from response
    ).sort("timestamp", -1).limit(limit)

    records = await cursor.to_list(length=limit)
    return {"history": records}


@router.delete("/")
async def clear_history(
    user_id: str = Depends(get_current_user),
    history_col=Depends(get_history_collection)
):
    """Delete all chat history for the logged-in user."""
    result = await history_col.delete_many({"user_id": user_id})
    return {"deleted": result.deleted_count}