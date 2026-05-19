from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import tasks, dashboard, users, ai

app = FastAPI(
    title="ТТМ — Система управления задачами",
    description="API для планирования, контроля и анализа задач. Хакатон Транстелематика.",
    version="1.0.0",
)

# CORS — фронтенд сможет делать запросы с любого origin (для хакатона ок)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tasks.router)
app.include_router(dashboard.router)
app.include_router(users.router)
app.include_router(ai.router)


@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "docs": "/docs"}
