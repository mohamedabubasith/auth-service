import os, secrets, json
from typing import List, Dict, Any
from pydantic_settings import BaseSettings


def get_cors_origins():
    cors_raw = os.getenv("CORS_ORIGINS", "*")
    if not cors_raw or cors_raw.strip() == "":
        return ["*"]
    
    # Try to parse as JSON first
    try:
        return json.loads(cors_raw)
    except:
        # Fall back to comma-separated string
        return [origin.strip() for origin in cors_raw.split(",") if origin.strip()]

class Settings(BaseSettings):
    # MongoDB
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb+srv://user:pass@abucluster.y8rtyqg.mongodb.net/?retryWrites=true&w=majority&appName=AbuCluster")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "auth_db")
    
    # Redis (Optional)
    REDIS_URL: str = os.getenv("REDIS_URL", "redis-123.crce214.us-east-1-3.ec2.redns.redis-cloud.com/123")
    ENABLE_REDIS: bool = os.getenv("ENABLE_REDIS", "false").lower() == "true"
    
    # JWT Settings  
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    
    # API Keys
    API_KEY_EXPIRE_DAYS: int = int(os.getenv("API_KEY_EXPIRE_DAYS", "365"))
    
    # Security
    PASSWORD_MIN_LENGTH: int = int(os.getenv("PASSWORD_MIN_LENGTH", "8"))
    MAX_LOGIN_ATTEMPTS: int = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
    LOCKOUT_DURATION_MINUTES: int = int(os.getenv("LOCKOUT_DURATION_MINUTES", "30"))
    
    # Email Settings
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "your-email")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "app_pasword")
    
    # URLs
    API_BASE_URL: str = os.getenv("API_BASE_URL", "https://bug-free-space-orbit-q7g6jg65rqr7345wg-8000.app.github.dev")
        
    # CORS
    CORS_ORIGINS: List[str] = get_cors_origins()
    
    # Tenants Configuration
    TENANTS: Dict[str, Dict[str, Any]] = {
        "kb": {
            "name": "Knowledgebase",
            "description": "Main KB",
            "settings": {
                "password_policy": {
                    "min_length": 8,
                    "require_special_chars": True
                },
                "features": ["api_keys", "password_reset", "email_verification"],
                "rate_limits": {
                    "login_attempts": 5,
                    "api_calls_per_hour": 1000
                }
            }
        }
    }
    
    # Default tenant
    DEFAULT_TENANT: str = os.getenv("DEFAULT_TENANT", "kb")
    
    class Config:
        env_file = ".env"

settings = Settings()