from pydantic_settings import BaseSettings 
from typing import List, Dict, Any
import secrets

class Settings(BaseSettings):
    # MongoDB
    MONGODB_URL: str = "mongodb+srv://abu:abu@abucluster.y8rtyqg.mongodb.net/?retryWrites=true&w=majority&appName=AbuCluster"
    DATABASE_NAME: str = "auth_db"
    
    # Redis (Optional - can be disabled for development)
    REDIS_URL: str = "redis-12560.crce214.us-east-1-3.ec2.redns.redis-cloud.com/12560"
    ENABLE_REDIS: bool = False  # Set to False to disable Redis features
    
    # JWT Settings
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1757262510
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # API Keys
    API_KEY_EXPIRE_DAYS: int = 365
    
    # Security
    PASSWORD_MIN_LENGTH: int = 8
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_DURATION_MINUTES: int = 30
    
    # Email Settings - Example with SendPulse (12,000 free emails/month)
    # SMTP_SERVER: str = "smtp.sendpulse.com"
    # SMTP_PORT: int = 587
    # SMTP_USERNAME: str = "your-sendpulse-username"
    # SMTP_PASSWORD: str = "your-sendpulse-password"
    # EMAIL_FROM: str = "noreply@yourapp.com"
    
    # Alternative: Gmail (500 emails/day free)
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = "mohamedabu.basith@gmail.com"
    SMTP_PASSWORD: str = "aerzvkjxlxgwxuaj"  # Use App Password, not regular password
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]

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
    
    # Default tenant (fallback)
    DEFAULT_TENANT: str = "kb"

    API_BASE_URL: str = "https://bug-free-space-orbit-q7g6jg65rqr7345wg-8000.app.github.dev"
    RESET_URL: str = "https://bug-free-space-orbit-q7g6jg65rqr7345wg-8000.app.github.dev"
    
    class Config:
        env_file = ".env"

settings = Settings()
