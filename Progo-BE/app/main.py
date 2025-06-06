from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import os
from pathlib import Path

from app.config import settings
from app.database import engine, get_db
from app.models.database import Base
from app.routers import (
    sensor_data_router, sessions_router, ml_router,
    workouts_router, reps_router, websocket_router
)
from app.utils.logging import setup_logging
from app.ml.inference import inference_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    setup_logging()
    
    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Create ML models directory
    models_dir = Path("app/ml/models")
    models_dir.mkdir(exist_ok=True)
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    
    # Load active ML model if available
    try:
        from app.database import get_sync_db
        db = next(get_sync_db())
        inference_engine.load_active_model(db, "default_classifier")
        db.close()
    except Exception as e:
        print(f"Warning: Could not load ML model on startup: {e}")
    
    print("🚀 Progo ML Backend started successfully!")
    
    yield
    
    # Shutdown
    print("🛑 Progo ML Backend shutting down...")


# Create FastAPI app
app = FastAPI(
    title=settings.project_name,
    description="ML-enabled IoT sensor data collection and exercise classification backend",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware - Production ready configuration
cors_origins = ["*"]  # Allow all origins for IoT devices
if settings.environment == "production":
    # In production, you might want to restrict origins
    # cors_origins = ["https://your-frontend-domain.com"]
    pass

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler to catch unhandled exceptions.
    """
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error",
            "detail": str(exc) if settings.debug else "An unexpected error occurred"
        }
    )


# Health check endpoint
@app.get("/", tags=["Health"])
async def root():
    """
    Root endpoint - health check.
    """
    return {
        "message": "Progo ML Backend",
        "status": "healthy",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Enhanced health check endpoint for Render monitoring.
    """
    health_data = {
        "status": "healthy",
        "environment": settings.environment,
        "version": "1.0.0",
        "timestamp": None,
        "checks": {}
    }
    
    # Check database connection
    try:
        from app.database import get_sync_db
        from sqlalchemy import text
        db = next(get_sync_db())
        db.execute(text("SELECT 1"))
        health_data["checks"]["database"] = "healthy"
        db.close()
    except Exception as e:
        health_data["checks"]["database"] = f"unhealthy: {str(e)}"
        health_data["status"] = "degraded"
    
    # Check ML model status
    ml_status = "loaded" if inference_engine.model_package else "not_loaded"
    health_data["checks"]["ml_model"] = ml_status
    
    # Check directories
    health_data["checks"]["logs_dir"] = "exists" if os.path.exists("logs") else "missing"
    health_data["checks"]["models_dir"] = "exists" if os.path.exists("app/ml/models") else "missing"
    
    # Add render-specific information
    if settings.is_render_environment():
        health_data["platform"] = "render"
        health_data["checks"]["render_env"] = "detected"
    
    return health_data
    
    return {
        "status": "healthy",
        "database": db_status,
        "ml_model": ml_status,
        "logs_directory": logs_exist,
        "models_directory": models_exist,
        "active_devices": len(inference_engine.sensor_buffers),
        "performance": inference_engine.get_performance_stats()
    }


# Include routers
app.include_router(sensor_data_router, prefix=settings.api_v1_str)
app.include_router(sessions_router, prefix=settings.api_v1_str)
app.include_router(ml_router, prefix=settings.api_v1_str)
app.include_router(workouts_router, prefix=settings.api_v1_str)
app.include_router(reps_router, prefix=settings.api_v1_str)
app.include_router(websocket_router)  # WebSocket doesn't need API prefix


# Additional utility endpoints
@app.get("/api/v1/info", tags=["System"])
async def get_system_info():
    """
    Get system information and configuration.
    """
    return {
        "project_name": settings.project_name,
        "debug_mode": settings.debug,
        "api_version": "v1",
        "ml_config": {
            "feature_window_size": settings.feature_window_size,
            "window_overlap": settings.window_overlap,
            "min_training_samples": settings.min_training_samples
        },
        "endpoints": {
            "sensor_data": f"{settings.api_v1_str}/sensor-data",
            "sessions": f"{settings.api_v1_str}/sessions", 
            "machine_learning": f"{settings.api_v1_str}/ml",
            "documentation": "/docs"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
