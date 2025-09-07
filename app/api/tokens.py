from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime, timedelta
from typing import List
from uuid import UUID

from app.models.user import User, APIKey
from app.schemas.auth import APIKeyCreate, APIKeyResponse
from app.core.auth import get_current_user, get_auth_service, AuthService
from app.core.security import generate_api_key, hash_api_key

router = APIRouter()

@router.post("/api-keys", response_model=APIKeyResponse)
async def create_api_key(
    api_key_data: APIKeyCreate,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)  # ✅ NEW: Get auth service
):
    # ✅ NEW: Check if tenant supports API keys feature
    if not auth_service.can_use_feature("api_keys"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"API keys are not enabled for tenant '{auth_service.tenant_id}'"
        )
    
    # Generate API key
    api_key = generate_api_key()
    key_hash = hash_api_key(api_key)
    
    # Calculate expiration
    expires_at = None
    if api_key_data.expires_days:
        expires_at = datetime.utcnow() + timedelta(days=api_key_data.expires_days)
    
    # ✅ UPDATED: Create tenant-aware API key record
    api_key_obj = APIKey(
        tenant_id=auth_service.tenant_id,  # ✅ NEW: Include tenant_id
        user_id=current_user.id,
        key_hash=key_hash,
        name=api_key_data.name,
        permissions=api_key_data.permissions or [],
        expires_at=expires_at
    )
    
    await api_key_obj.insert()
    
    return APIKeyResponse(
        id=api_key_obj.id,
        name=api_key_obj.name,
        key=api_key,  # Only returned on creation
        permissions=api_key_data.permissions or [],
        created_at=api_key_obj.created_at.isoformat()
    )

@router.get("/api-keys")
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)  # ✅ NEW: Get auth service
):
    # ✅ NEW: Check feature availability
    if not auth_service.can_use_feature("api_keys"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"API keys are not enabled for tenant '{auth_service.tenant_id}'"
        )
    
    # ✅ UPDATED: Tenant-aware query
    api_keys = await APIKey.find(
        APIKey.tenant_id == auth_service.tenant_id,  # ✅ NEW: Filter by tenant
        APIKey.user_id == current_user.id,
        APIKey.is_active == True
    ).to_list()
    
    return [
        {
            "id": key.id,
            "name": key.name,
            "permissions": key.permissions,
            "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
            "expires_at": key.expires_at.isoformat() if key.expires_at else None,
            "created_at": key.created_at.isoformat(),
            "tenant_id": key.tenant_id  # ✅ NEW: Include tenant info in response
        }
        for key in api_keys
    ]

@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: UUID,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)  # ✅ NEW: Get auth service
):
    # ✅ NEW: Check feature availability
    if not auth_service.can_use_feature("api_keys"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"API keys are not enabled for tenant '{auth_service.tenant_id}'"
        )
    
    # ✅ UPDATED: Tenant-aware query
    api_key = await APIKey.find_one(
        APIKey.tenant_id == auth_service.tenant_id,  # ✅ NEW: Filter by tenant
        APIKey.id == key_id,
        APIKey.user_id == current_user.id
    )
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    api_key.is_active = False
    await api_key.save()
    
    return {
        "message": "API key revoked successfully",
        "tenant_id": auth_service.tenant_id  # ✅ NEW: Include tenant info
    }

# ✅ NEW: Additional endpoint to get API key usage stats
@router.get("/api-keys/{key_id}/stats")
async def get_api_key_stats(
    key_id: UUID,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Get usage statistics for a specific API key"""
    if not auth_service.can_use_feature("api_keys"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"API keys are not enabled for tenant '{auth_service.tenant_id}'"
        )
    
    api_key = await APIKey.find_one(
        APIKey.tenant_id == auth_service.tenant_id,
        APIKey.id == key_id,
        APIKey.user_id == current_user.id,
        APIKey.is_active == True
    )
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    # Calculate days since creation
    days_active = (datetime.utcnow() - api_key.created_at).days
    
    return {
        "key_id": api_key.id,
        "name": api_key.name,
        "created_at": api_key.created_at.isoformat(),
        "last_used_at": api_key.last_used_at.isoformat() if api_key.last_used_at else None,
        "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else "Never",
        "days_active": days_active,
        "is_expired": api_key.expires_at < datetime.utcnow() if api_key.expires_at else False,
        "permissions": api_key.permissions,
        "tenant_id": api_key.tenant_id
    }

# ✅ NEW: Endpoint to update API key permissions
@router.put("/api-keys/{key_id}")
async def update_api_key(
    key_id: UUID,
    name: str = None,
    permissions: List[str] = None,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Update API key name and permissions"""
    if not auth_service.can_use_feature("api_keys"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"API keys are not enabled for tenant '{auth_service.tenant_id}'"
        )
    
    api_key = await APIKey.find_one(
        APIKey.tenant_id == auth_service.tenant_id,
        APIKey.id == key_id,
        APIKey.user_id == current_user.id,
        APIKey.is_active == True
    )
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    # Update fields if provided
    if name is not None:
        api_key.name = name
    
    if permissions is not None:
        api_key.permissions = permissions
    
    await api_key.save()
    
    return {
        "message": "API key updated successfully",
        "id": api_key.id,
        "name": api_key.name,
        "permissions": api_key.permissions,
        "tenant_id": api_key.tenant_id
    }
