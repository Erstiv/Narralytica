from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api import episodes, scenes, search

app = FastAPI(
    title="Narralytica API",
    description="Natural-Language Video Intelligence Platform",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3002",
        "http://localhost:3001",
        "http://localhost:3000",
        "https://captainofindustries.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(episodes.router, prefix="/api")
app.include_router(scenes.router, prefix="/api")
app.include_router(search.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "service": "narralytica",
        "environment": settings.environment,
    }
