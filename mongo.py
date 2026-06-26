from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient
from contextlib import asynccontextmanager
from milvus_crossencoding import build_bm25_index


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.mongo = AsyncIOMotorClient("mongodb://localhost:27017")
    db_collection = app.state.mongo["ragdb"]["rag_books"]
    await build_bm25_index(db_collection)
    yield
    app.state.mongo.close()


async def connect_db():
    from app import app
    return app.state.mongo["ragdb"]["rag_books"]