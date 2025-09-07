from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timedelta

from app.models.user import User
from app.models.token import Token, TokenType
from app.schemas.auth import LoginRequest, TokenResponse, ValidationRequest, ValidationResponse
from app.schemas.user import UserCreate, UserResponse
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, verify_token
from app.core.auth import AuthService, get_current_user, get_tenant_id, get_auth_service
from app.utils.email import send_password_reset_email
from app.config import settings
import secrets

router = APIRouter()
security = HTTPBearer()

@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    auth_service: AuthService = Depends(get_auth_service)
):
    # Check if user exists in this tenant
    if await auth_service.get_user_by_email(user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered in this tenant"
        )
    
    # ✅ Use tenant-specific password validation
    is_valid, message = auth_service.validate_password_policy(user_data.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    # Create tenant-specific user
    hashed_password = hash_password(user_data.password)
    user = User(
        tenant_id=auth_service.tenant_id,
        email=user_data.email,
        password_hash=hashed_password,
        is_verified=True
    )
    
    await user.insert()
    return user

@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: LoginRequest,
    tenant_id: str = Depends(get_tenant_id)
):
    auth_service = AuthService(tenant_id)
    
    user = await auth_service.get_user_by_email(login_data.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    if auth_service.is_user_locked(user):
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account is locked due to too many failed attempts"
        )
    
    if not verify_password(login_data.password, user.password_hash):
        await auth_service.increment_failed_attempts(user)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is inactive"
        )
    
    await auth_service.reset_failed_attempts(user)
    
    # ✅ Include tenant_id in JWT payload
    access_token = create_access_token({
        "sub": str(user.id),
        "tenant_id": tenant_id
    })
    refresh_token = create_refresh_token({
        "sub": str(user.id),
        "tenant_id": tenant_id
    })
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

@router.post("/validate", response_model=ValidationResponse)
async def validate_token_endpoint(
    validation_data: ValidationRequest,
    tenant_id: str = Depends(get_tenant_id)
):
    payload = verify_token(validation_data.token)
    
    if not payload:
        return ValidationResponse(is_valid=False)
    
    # Verify tenant matches
    token_tenant = payload.get("tenant_id")
    if token_tenant != tenant_id:
        return ValidationResponse(is_valid=False)
    
    return ValidationResponse(
        is_valid=True,
        user_id=payload.get("sub"),
        expires_at=str(datetime.fromtimestamp(payload.get("exp", 0)))
    )

@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    auth_service = AuthService(tenant_id)
    token = credentials.credentials
    
    # ✅ Blacklist the JWT token to invalidate it immediately
    payload = verify_token(token)
    if payload:
        exp = payload.get("exp")
        if exp:
            # Calculate remaining time until token expires
            expires_in = exp - int(datetime.utcnow().timestamp())
            if expires_in > 0:
                # Add token to blacklist with TTL
                auth_service.blacklist_token(token, expires_in)
                print(f"✅ Token blacklisted for user {current_user.email} in tenant {tenant_id}")
    
    return {
        "message": "Successfully logged out", 
        "tenant": tenant_id,
        "user": current_user.email
    }

@router.post("/forgot-password")
async def forgot_password(
    email: str,
    tenant_id: str = Depends(get_tenant_id)
):
    auth_service = AuthService(tenant_id)
    
    user = await auth_service.get_user_by_email(email)
    if not user:
        # Return success message even if user doesn't exist (security best practice)
        return {"message": "If the email exists, a reset link has been sent"}
    
    # Generate tenant-specific reset token
    reset_token = secrets.token_urlsafe(32)
    
    # Save token to database
    token = Token(
        tenant_id=tenant_id,
        user_id=user.id,
        token_hash=reset_token,
        token_type=TokenType.RESET,
        expires_at=datetime.utcnow() + timedelta(hours=1)
    )
    await token.insert()
    
    # ✅ NEW: Send the actual password reset email
    email_sent = await send_password_reset_email(
        to_email=email,
        reset_token=reset_token,
        tenant_id=tenant_id
    )
    
    if not email_sent:
        print(f"⚠️  Warning: Failed to send reset email to {email} for tenant {tenant_id}")
        # Still return success message for security reasons
    
    return {"message": "If the email exists, a reset link has been sent"}


from app.schemas.auth import ResetPasswordRequest

@router.post("/reset-password")
async def reset_password(
    reset_data: ResetPasswordRequest,
    tenant_id: str = Depends(get_tenant_id)
):
    """Reset user password using the token from email"""
    auth_service = AuthService(tenant_id)
    
    # Find valid reset token
    token = await Token.find_one(
        Token.tenant_id == tenant_id,
        Token.token_hash == reset_data.token,
        Token.token_type == TokenType.RESET,
        Token.is_revoked == False,
        Token.expires_at > datetime.utcnow()
    )
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Get user and validate
    user = await auth_service.get_user_by_id(str(token.user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found"
        )
    
    # Validate new password against tenant policy
    is_valid, message = auth_service.validate_password_policy(reset_data.new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    # Update password and revoke token
    user.password_hash = hash_password(reset_data.new_password)
    user.updated_at = datetime.utcnow()
    await user.save()
    
    # Revoke the reset token (single use)
    token.is_revoked = True
    await token.save()
    
    return {
        "message": "Password reset successfully",
        "tenant_id": tenant_id
    }
