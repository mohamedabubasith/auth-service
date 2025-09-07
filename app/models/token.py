from beanie import Document, Indexed
from pydantic import Field
from typing import Optional
from datetime import datetime
from uuid import UUID, uuid4
import enum

class TokenType(str, enum.Enum):
    ACCESS = "access"
    REFRESH = "refresh"
    RESET = "reset"
    VERIFY = "verify"

class Token(Document):
    id: UUID = Field(default_factory=uuid4, alias="_id")
    tenant_id: Indexed(str)  # ✅ NEW: Tenant identifier
    user_id: UUID
    token_hash: Indexed(str)
    token_type: TokenType
    is_revoked: bool = False
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "tokens"
        indexes = [
            "token_hash",
            "tenant_id",
            "user_id",
            "expires_at",
            "created_at"
        ]
