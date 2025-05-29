from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    database_url: str = "postgresql://postgres:password@localhost:5432/progo_db"
    database_url_async: str = "postgresql+asyncpg://postgres:password@localhost:5432/progo_db"
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


settings = Settings()
