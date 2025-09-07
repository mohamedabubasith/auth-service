from fastapi import APIRouter
from app.config import settings

router = APIRouter()

@router.get("/config")
async def get_config():
    """Get public configuration for frontend"""
    return {
        "apiBaseUrl": settings.API_BASE_URL,
        "tenants": list(settings.TENANTS.keys())
    }
