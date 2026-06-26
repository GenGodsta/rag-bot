from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient
from contextlib import asynccontextmanager
from milvus_crossencoding import build_bm25_index


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.mongo = AsyncIOMotorClient("mongodb://localhost:27017")
    db = app.state.mongo["ragdb"]

    # existing
    db_collection = db["rag_books"]
    await build_bm25_index(db_collection)

    # new indexes
    await db["users"].create_index("username", unique=True)
    await db["users"].create_index("user_id", unique=True)
    await db["chat_history"].create_index("user_id")

    yield
    app.state.mongo.close()

async def connect_db():
    from app import app
    return app.state.mongo["ragdb"]["rag_books"]