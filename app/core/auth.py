from fastapi import Depends, HTTPException, status, Request, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from uuid import UUID

from datetime import datetime, timedelta
from typing import Optional, Any, Dict
import redis
import re
from app.models.user import User, APIKey, Tenant
from app.models.token import Token, TokenType
from app.core.security import verify_token, hash_api_key
from app.core.tenant_manager import TenantManager
from app.config import settings

security = HTTPBearer()

# Initialize Redis client only if enabled
redis_client = None
if settings.ENABLE_REDIS:
    try:
        redis_client = redis.from_url(settings.REDIS_URL)
        redis_client.ping()
    except:
        print("Warning: Redis connection failed. Rate limiting and token blacklisting disabled.")
        redis_client = None

async def get_tenant_id(
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
    request: Request = None
) -> str:
    """Extract tenant ID from header or other sources"""
    
    # Only use X-Tenant-ID header
    tenant = x_tenant_id
    
    if not tenant and request:
        # Try query parameter
        tenant = request.query_params.get("tenant_id")
    
    if not tenant and request:
        # Try subdomain (e.g., app1.yourservice.com)
        host = request.headers.get("host", "")
        if "." in host:
            subdomain = host.split(".")[0]
            if subdomain in settings.TENANTS.keys():
                tenant = subdomain
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant ID is required. Provide via X-Tenant-ID header or query parameter."
        )
    
    # Validate tenant exists
    if not await TenantManager.is_valid_tenant(tenant):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant}' not found or inactive"
        )
    
    return tenant

class AuthService:
    """Enhanced AuthService with tenant-specific policies and settings"""
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.tenant_manager = TenantManager()

    async def get_user_by_email(self, email: str) -> Optional[User]:
        return await User.find_one(
            User.tenant_id == self.tenant_id,
            User.email == email
        )

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        print(f"🔍 Looking for user ID: {user_id} in tenant: {self.tenant_id}")
        
        try:
            # Convert string to UUID object
            user_uuid = UUID(user_id)
        except ValueError:
            # Fallback to original string if conversion fails
            user_uuid = user_id
            print(f"⚠️ Could not convert {user_id} to UUID, using as string")
        
        user = await User.find_one(
            User.tenant_id == self.tenant_id,
            User.id == user_uuid  # Now using UUID object
        )
        
        print(f"✅ User found: {user is not None}")
        if user:
            print(f"👤 Found user: {user.email}")
        
        return user

    def is_user_locked(self, user: User) -> bool:
        if user.locked_until and user.locked_until > datetime.utcnow():
            return True
        return False

    async def increment_failed_attempts(self, user: User):
        """Increment failed attempts with tenant-specific limits"""
        user.failed_login_attempts += 1
        
        # ✅ Use tenant-specific max login attempts
        max_attempts = self.tenant_manager.get_rate_limit(
            self.tenant_id, 
            "login_attempts"
        )
        
        if user.failed_login_attempts >= max_attempts:
            user.locked_until = datetime.utcnow() + timedelta(
                minutes=settings.LOCKOUT_DURATION_MINUTES
            )
        user.updated_at = datetime.utcnow()
        await user.save()

    async def reset_failed_attempts(self, user: User):
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login = datetime.utcnow()
        user.updated_at = datetime.utcnow()
        await user.save()

    def is_token_blacklisted(self, token: str) -> bool:
        if not redis_client:
            return False
        try:
            return redis_client.exists(f"blacklist:{self.tenant_id}:{token}")
        except:
            return False

    def blacklist_token(self, token: str, expires_in: int):
        if redis_client:
            try:
                redis_client.setex(f"blacklist:{self.tenant_id}:{token}", expires_in, "true")
            except:
                pass

    async def validate_api_key(self, api_key: str) -> Optional[User]:
        """Validate API key with tenant-specific feature check"""
        
        # ✅ Check if API keys are enabled for this tenant
        if not self.tenant_manager.is_feature_enabled(self.tenant_id, "api_keys"):
            return None
        
        key_hash = hash_api_key(api_key)
        api_key_obj = await APIKey.find_one(
            APIKey.tenant_id == self.tenant_id,
            APIKey.key_hash == key_hash,
            APIKey.is_active == True
        )
        
        if not api_key_obj:
            return None
            
        if api_key_obj.expires_at and api_key_obj.expires_at < datetime.utcnow():
            return None
            
        api_key_obj.last_used_at = datetime.utcnow()
        await api_key_obj.save()
        
        return await self.get_user_by_id(str(api_key_obj.user_id))

    # ✅ NEW: Tenant-specific password validation
    def validate_password_policy(self, password: str) -> tuple[bool, str]:
        """Validate password against tenant-specific policy"""
        policy = self.tenant_manager.get_password_policy(self.tenant_id)
        
        # Check minimum length
        min_length = policy.get("min_length", settings.PASSWORD_MIN_LENGTH)
        if len(password) < min_length:
            return False, f"Password must be at least {min_length} characters long"
        
        # Check special characters
        if policy.get("require_special_chars", False):
            if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
                return False, "Password must contain at least one special character"
        
        # Check numbers
        if policy.get("require_numbers", False):
            if not re.search(r'\d', password):
                return False, "Password must contain at least one number"
        
        # Check uppercase
        if policy.get("require_uppercase", False):
            if not re.search(r'[A-Z]', password):
                return False, "Password must contain at least one uppercase letter"
        
        return True, "Password meets policy requirements"

    # ✅ NEW: Feature availability checks
    def can_use_feature(self, feature: str) -> bool:
        """Check if tenant can use a specific feature"""
        return self.tenant_manager.is_feature_enabled(self.tenant_id, feature)

    # ✅ NEW: Get tenant-specific settings
    def get_setting(self, setting_path: str, default: Any = None) -> Any:
        """Get tenant-specific setting"""
        return self.tenant_manager.get_tenant_setting(self.tenant_id, setting_path, default)

    # ✅ NEW: Tenant info for responses
    def get_tenant_info(self) -> Dict[str, str]:
        """Get tenant display information"""
        return self.tenant_manager.get_tenant_info(self.tenant_id)
    
async def get_auth_service(tenant_id: str = Depends(get_tenant_id)) -> AuthService:
    """Dependency to get AuthService for current tenant"""
    return AuthService(tenant_id)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    tenant_id: str = Depends(get_tenant_id)
) -> User:
    """Enhanced user authentication with tenant management"""
    auth_service = AuthService(tenant_id)
    
    token = credentials.credentials
    
    # Check if it's an API key
    if token.startswith("ak_"):
        user = await auth_service.validate_api_key(token)
        if not user:
            # ✅ More descriptive error for disabled API keys
            if not auth_service.can_use_feature("api_keys"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="API keys are not enabled for this tenant"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid API key"
                )
        return user
    
    # Check if token is blacklisted
    if auth_service.is_token_blacklisted(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked"
        )
    
    # Verify JWT token
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    # Verify tenant matches token
    token_tenant = payload.get("tenant_id")
    if token_tenant != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token tenant mismatch"
        )
    
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    user = await auth_service.get_user_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive"
        )
    
    return user

# ✅ NEW: Helper dependency for getting auth service
async def get_auth_service(tenant_id: str = Depends(get_tenant_id)) -> AuthService:
    """Dependency to get AuthService for current tenant"""
    return AuthService(tenant_id)

# ✅ NEW: Optional authentication (for public endpoints)
async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    tenant_id: str = Depends(get_tenant_id)
) -> Optional[User]:
    """Optional authentication - returns None if no token provided"""
    if not credentials:
        return None
    
    try:
        # Use the same logic as get_current_user but don't raise exceptions
        auth_service = AuthService(tenant_id)
        token = credentials.credentials
        
        if token.startswith("ak_"):
            return await auth_service.validate_api_key(token)
        
        if auth_service.is_token_blacklisted(token):
            return None
        
        payload = verify_token(token)
        if not payload or payload.get("tenant_id") != tenant_id:
            return None
        
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        user = await auth_service.get_user_by_id(user_id)
        return user if user and user.is_active else None
        
    except:
        return None
