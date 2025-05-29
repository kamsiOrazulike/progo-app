from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # Environment detection
    environment: str = "development"
    
    # Database configuration with environment-aware defaults
    database_url: str = "sqlite:///./progo_dev.db"
    database_url_async: str = "sqlite+aiosqlite:///./progo_dev.db"
    
    # Security
    secret_key: str = "your-secret-key-change-in-production"
    debug: bool = True
    log_level: str = "INFO"
    
    # ML Settings
    model_update_interval: int = 3600
    min_training_samples: int = 100
    feature_window_size: int = 200
    window_overlap: float = 0.5
    
    # API Settings
    api_v1_str: str = "/api/v1"
    project_name: str = "Progo ML Backend"
    
    # Redis Settings (optional)
    redis_url: Optional[str] = "redis://localhost:6379/0"
    
    # Additional ML inference settings
    inference_window_size: int = 100
    inference_overlap: float = 0.5
    model_save_path: str = "app/ml/models"
    
    class Config:
        env_file = ".env"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Auto-configure for Render environment
        if self.is_render_environment():
            self.configure_for_render()
    
    def is_render_environment(self) -> bool:
        """Detect if running on Render"""
        return (
            os.getenv("RENDER") == "true" or 
            os.getenv("ENVIRONMENT") == "production" or
            "DATABASE_URL" in os.environ
        )
    
    def configure_for_render(self):
        """Configure settings for Render deployment"""
        # Use Render's provided DATABASE_URL
        if render_db_url := os.getenv("DATABASE_URL"):
            self.database_url = render_db_url
            # Convert sync URL to async for SQLAlchemy
            if render_db_url.startswith("postgres://"):
                self.database_url_async = render_db_url.replace("postgres://", "postgresql+asyncpg://", 1)
            elif render_db_url.startswith("postgresql://"):
                self.database_url_async = render_db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        
        # Production settings
        self.debug = False
        self.environment = "production"
        
        # Use environment variables
        if secret := os.getenv("SECRET_KEY"):
            self.secret_key = secret


settings = Settings()
