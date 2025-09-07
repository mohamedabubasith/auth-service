from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import connect_to_mongo, close_mongo_connection
from app.api import auth, users, tokens, config


# Rate limiter (only if Redis is enabled)
limiter = None
if settings.ENABLE_REDIS:
    try:
        limiter = Limiter(key_func=get_remote_address, storage_uri=settings.REDIS_URL)
    except:
        print("Warning: Redis not available. Rate limiting disabled.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_to_mongo()
    yield
    # Shutdown
    await close_mongo_connection()

app = FastAPI(
    title="Authentication Service",
    description="Centralized authentication provider with JWT and API key support",
    version="1.0.0",
    lifespan=lifespan
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# Add rate limiting only if Redis is available
if limiter:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/auth", tags=["Users"])
app.include_router(tokens.router, prefix="/auth", tags=["Tokens"])
app.include_router(config.router, prefix="", tags=["Configs"])

@app.get("/")
def root():
    return {"message": "Authentication Service API", "version": "1.0.0"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
