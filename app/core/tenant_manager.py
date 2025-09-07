from typing import Dict, Any, Optional, List
from app.config import settings
from app.models.user import Tenant

class TenantManager:
    """Manages tenant-specific configurations and policies"""
    
    @staticmethod
    def get_tenant_config(tenant_id: str) -> Dict[str, Any]:
        """Get complete tenant configuration from settings"""
        return settings.TENANTS.get(tenant_id, settings.TENANTS[settings.DEFAULT_TENANT])
    
    @staticmethod
    def get_tenant_setting(tenant_id: str, setting_path: str, default: Any = None) -> Any:
        """
        Get specific tenant setting using dot notation
        Example: get_tenant_setting("app1", "password_policy.min_length", 8)
        """
        config = TenantManager.get_tenant_config(tenant_id)
        
        # Navigate through nested settings using dot notation
        keys = setting_path.split(".")
        value = config.get("settings", {})
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    @staticmethod
    def is_feature_enabled(tenant_id: str, feature: str) -> bool:
        """Check if a feature is enabled for a tenant"""
        features = TenantManager.get_tenant_setting(tenant_id, "features", [])
        return feature in features
    
    @staticmethod
    def get_rate_limit(tenant_id: str, limit_type: str) -> int:
        """Get rate limit for a specific tenant"""
        return TenantManager.get_tenant_setting(
            tenant_id, 
            f"rate_limits.{limit_type}", 
            default=getattr(settings, limit_type.upper(), 5)
        )
    
    @staticmethod
    def get_password_policy(tenant_id: str) -> Dict[str, Any]:
        """Get complete password policy for tenant"""
        return TenantManager.get_tenant_setting(
            tenant_id,
            "password_policy",
            default={
                "min_length": settings.PASSWORD_MIN_LENGTH,
                "require_special_chars": False,
                "require_numbers": False,
                "require_uppercase": False,
                "require_2fa": False
            }
        )
    
    @staticmethod
    async def is_valid_tenant(tenant_id: str) -> bool:
        """Validate if tenant exists in config and database"""
        # Check config first
        if tenant_id not in settings.TENANTS:
            return False
        
        # Check database for active status
        tenant = await Tenant.find_one(Tenant.tenant_id == tenant_id)
        return tenant is not None and tenant.is_active
    
    @staticmethod
    def get_tenant_info(tenant_id: str) -> Dict[str, str]:
        """Get tenant display information"""
        config = TenantManager.get_tenant_config(tenant_id)
        return {
            "tenant_id": tenant_id,
            "name": config.get("name", "Unknown"),
            "description": config.get("description", "")
        }
