from beanie import Document, Indexed
from pydantic import EmailStr, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID, uuid4

from beanie import Document, Indexed
from pydantic import EmailStr, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID, uuid4

class User(Document):
    id: UUID = Field(default_factory=uuid4, alias="_id")
    tenant_id: Indexed(str)  # ✅ NEW: Tenant identifier
    email: EmailStr  # Remove unique=True constraint
    password_hash: str
    is_active: bool = True
    is_verified: bool = False
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None
    last_login: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "users"
        indexes = [
            [("tenant_id", 1), ("email", 1)],  # ✅ Compound unique index
            "tenant_id",
            "email",
            "created_at"
        ]

class APIKey(Document):
    id: UUID = Field(default_factory=uuid4, alias="_id")
    tenant_id: Indexed(str)  # ✅ NEW: Tenant identifier
    user_id: UUID
    key_hash: Indexed(str, unique=True)
    name: str
    permissions: List[str] = []
    is_active: bool = True
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "api_keys"
        indexes = [
            "key_hash",
            "tenant_id",
            "user_id",
            "created_at"
        ]

class Tenant(Document):
    id: UUID = Field(default_factory=uuid4, alias="_id")
    tenant_id: Indexed(str, unique=True)  # ✅ NEW: Tenant model
    name: str
    description: Optional[str] = None
    is_active: bool = True
    settings: dict = {}
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "tenants"
        indexes = [
            "tenant_id",
            "created_at"
        ]
