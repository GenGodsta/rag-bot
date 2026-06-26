from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mongo import lifespan
from routers import chat
from authorization import router as auth_router
from history import router as history_router

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