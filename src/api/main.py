"""
FastAPI application entry point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import sys

from src.config.settings import get_settings
from src.api.routes import router

# ── Configure logging ─────────────────────────────────────
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - {message}",
    level="INFO",
)
logger.add(
    "logs/agent.log",
    rotation="10 MB",
    retention="7 days",
    level="DEBUG",
)

# ── Create app ────────────────────────────────────────────
app = FastAPI(
    title="Job Application Agent API",
    description="AI-powered resume tailoring with format preservation",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ────────────────────────────────────────────────
app.include_router(router, prefix="/api")


@app.on_event("startup")
async def startup():
    """Validate configuration on startup."""
    settings = get_settings()

    if not settings.GROQ_API_KEY:
        logger.warning("⚠️  GROQ_API_KEY not set — Groq calls will fail")
    else:
        logger.info("✅ Groq API key configured")

    if not settings.GEMINI_API_KEY:
        logger.warning("⚠️  GEMINI_API_KEY not set — Gemini fallback unavailable")
    else:
        logger.info("✅ Gemini API key configured")

    logger.info(f"📁 Output directory: {settings.output_path}")
    logger.info("🚀 Job Application Agent API is ready")


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "src.api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
    )
