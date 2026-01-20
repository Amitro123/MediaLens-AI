"""FastAPI application entry point for DevLens AI"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from app.api.routes import router
from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="MediaLens AI",
    description="Turn video content into searchable intelligence",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5176",  # New Vite port
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5176",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
from app.api.routes import router, minimal_router
app.include_router(router)
app.include_router(minimal_router)

# Mount static files for upload access
from fastapi.staticfiles import StaticFiles
upload_path = settings.get_upload_path()
app.mount("/uploads", StaticFiles(directory=upload_path), name="uploads")


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "MediaLens AI",
        "version": "0.1.0",
        "description": "Turn video content into searchable intelligence",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}


@app.on_event("startup")
async def startup_event():
    """Application startup tasks"""
    # Trigger reload for prompt fix
    logger.info("Starting MediaLens AI...")
    logger.info(f"Upload directory: {settings.upload_dir}")
    
    # Create upload directory
    settings.get_upload_path()
    
    logger.info("MediaLens AI started successfully")

    # Issue 3: Better Fallback Message for Gemini
    import os
    gemini_key = settings.gemini_api_key
    
    if not gemini_key or "dummy" in gemini_key.lower() or gemini_key.startswith("todo"):
        logger.warning("="*80)
        logger.warning("⚠️  WARNING: Gemini API key not configured or invalid")
        logger.warning("⚠️  Semantic video analysis will be DISABLED")
        logger.warning("⚠️  The system will use regular frame sampling instead")
        logger.warning("⚠️  To enable: Set GEMINI_API_KEY environment variable")
        logger.warning("⚠️  Get key at: https://aistudio.google.com/apikey")
        logger.warning("="*80)
    else:
        logger.info("✅ Gemini API key configured")

    # Groq API check for fast STT
    groq_key = settings.groq_api_key
    if groq_key:
        logger.info("✅ Groq API configured (fast STT)")
    else:
        logger.warning("="*80)
        logger.warning("⚠️  Groq API not configured")
        logger.warning("⚠️  STT will use CPU Whisper (SLOW - 5+ min per video)")
        logger.warning("⚠️  For 100x faster transcription:")
        logger.warning("⚠️    1. Get free key: https://console.groq.com/")
        logger.warning("⚠️    2. Set: GROQ_API_KEY=your_key")
        logger.warning("="*80)


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown tasks"""
    logger.info("Shutting down MediaLens AI...")
    
    # Gracefully fail any in-progress sessions
    try:
        from app.services.session_manager import get_session_manager
        session_manager = get_session_manager()
        
        # Get all sessions
        all_sessions = session_manager.get_all_sessions()
        
        # Fail any that are still processing
        for session_id, session_data in all_sessions.items():
            if session_data.get("status") == "processing":
                logger.warning(f"Failing in-progress session {session_id} due to server shutdown")
                session_manager.fail(
                    session_id, 
                    "Server restarted during processing. Please try again."
                )
    except Exception as e:
        logger.error(f"Error during graceful shutdown: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
