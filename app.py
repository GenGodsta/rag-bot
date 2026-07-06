from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from mongo import lifespan as mongo_lifespan
from routers import chat
from authorization import router as auth_router
from history import router as history_router
from mcp_instance import mcp_client

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with mongo_lifespan(app):
        await mcp_client.connect()
        yield
        await mcp_client.close()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(auth_router)
app.include_router(history_router)
app.include_router(chat.router, prefix="/api/chat")