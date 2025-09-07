from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime

from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate, PasswordUpdate
from app.core.auth import get_current_user
from app.core.security import hash_password, verify_password
from app.config import settings

router = APIRouter()

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user

@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
):
    if user_update.email:
        if user_update.email != current_user.email:
            current_user.email = user_update.email
            current_user.is_verified = False

    current_user.updated_at = datetime.utcnow()
    await current_user.save()
    return current_user

@router.post("/change-password")
async def change_password(
    password_update: PasswordUpdate,
    current_user: User = Depends(get_current_user),
):
    if not verify_password(password_update.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    if len(password_update.new_password) < settings.PASSWORD_MIN_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters"
        )

    current_user.password_hash = hash_password(password_update.new_password)
    current_user.updated_at = datetime.utcnow()
    await current_user.save()
    return {"message": "Password updated successfully"}

@router.delete("/me")
async def delete_current_user(current_user: User = Depends(get_current_user)):
    current_user.is_active = False
    current_user.updated_at = datetime.utcnow()
    await current_user.save()
    return {"message": "Account deactivated successfully"}
