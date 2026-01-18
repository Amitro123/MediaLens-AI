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
    allow_origins=["*"],  # Configure appropriately for production
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
    logger.info("Starting MediaLens AI...")
    logger.info(f"Upload directory: {settings.upload_dir}")
    
    # Create upload directory
    settings.get_upload_path()
    
    logger.info("MediaLens AI started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown tasks"""
    logger.info("Shutting down MediaLens AI...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
