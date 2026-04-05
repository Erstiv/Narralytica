from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.api import episodes, scenes, search, exports, library, processing, tweaks, analytics, media, reports

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
        "https://weftwarp.com",
        "http://weftwarp.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(episodes.router, prefix="/api")
app.include_router(scenes.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(exports.router, prefix="/api")
app.include_router(library.router, prefix="/api")
app.include_router(processing.router, prefix="/api")
app.include_router(tweaks.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(media.router, prefix="/api")
app.include_router(reports.router, prefix="/api")

# Serve extracted media (thumbnails + clips) from /app/media
app.mount("/api/media-static", StaticFiles(directory=settings.media_dir), name="media-static")


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "service": "narralytica",
        "environment": settings.environment,
    }
