from typing import List, Optional, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings
import secrets


class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    
    DATABASE_URL: str = "postgresql://postgres:postgres@database:5432/video_annotation"
    REDIS_URL: str = "redis://redis:6379/0"
    
    SAM_SERVICE_URL: str = "http://sam-service:8001"
    UPLOAD_DIR: str = "/app/uploads"
    MAX_FILE_SIZE: int = 500 * 1024 * 1024  # 500MB
    
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://frontend:3000",
    ]
    
    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    PROJECT_NAME: str = "Medical Video Annotation"
    
    model_config = {"env_file": ".env"}


settings = Settings()