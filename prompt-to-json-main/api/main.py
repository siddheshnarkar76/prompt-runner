"""
FastAPI Main Application
Production-ready API server for AI Design Platform with CreatorCore integration.

This server replaces Flask mcp_server.py with a clean, modular FastAPI architecture.
All existing functionality is preserved but organized according to production standards.
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.health import router as health_router
from api.routes import core_router, mcp_router
from api.orchestrator import orchestrator_router
from mcp.db import get_database, close_database

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for database connections and resources."""
    logger.info("Starting FastAPI application...")
    
    # Initialize database connection
    db = get_database()
    logger.info(f"Connected to MongoDB database: {db.name}")
    
    # Verify collections exist
    collections = db.list_collection_names()
    logger.info(f"Available collections: {len(collections)}")
    
    yield
    
    # Cleanup on shutdown
    logger.info("Shutting down FastAPI application...")
    close_database()


# Create FastAPI application
app = FastAPI(
    title="AI Design Platform API",
    description="Production-ready backend for CreatorCore integration",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware for local development and Streamlit integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": "Internal server error", "detail": str(exc)}
    )


# Include routers
app.include_router(health_router, prefix="/system", tags=["Health"])
app.include_router(core_router, prefix="/core", tags=["CreatorCore"])
app.include_router(mcp_router, prefix="/api/mcp", tags=["MCP"])
app.include_router(orchestrator_router, prefix="/orchestrate", tags=["Orchestrator"])


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "AI Design Platform API",
        "version": "2.0.0",
        "status": "active",
        "message": "MCP API server is running",
        "endpoints": [
            "GET /api/mcp",
            "POST /api/mcp/save_rule",
            "GET /api/mcp/list_rules",
            "POST /api/mcp/geometry",
            "POST /api/mcp/feedback",
            "GET /core/status",
            "POST /core/log",
            "POST /core/feedback",
            "GET /core/context",
            "POST /orchestrate/run",
            "GET /system/health"
        ],
        "docs": "/docs",
        "health": "/system/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=5001,
        reload=True,
        log_level="info"
    )
