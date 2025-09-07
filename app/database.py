from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.models.user import User, APIKey, Tenant
from app.models.token import Token
from app.config import settings

class Database:
    client: AsyncIOMotorClient = None
    database = None

db = Database()

async def connect_to_mongo():
    """Create database connection"""
    db.client = AsyncIOMotorClient(settings.MONGODB_URL)
    db.database = db.client[settings.DATABASE_NAME]
    
    # ✅ Include all document models including Tenant
    await init_beanie(
        database=db.database,
        document_models=[User, APIKey, Token, Tenant]
    )
    
    # Create default tenants for your 3 apps
    await create_default_tenants()
    
    print("✅ MongoDB connected and Beanie initialized")

async def close_mongo_connection():
    """Close database connection"""
    if db.client:
        db.client.close()

async def create_default_tenants():
    """Create/update tenants based on config settings"""
    from app.models.user import Tenant
    from app.config import settings
    
    print("📋 Setting up tenants from configuration...")
    
    for tenant_id, tenant_config in settings.TENANTS.items():
        # Check if tenant already exists
        existing = await Tenant.find_one(Tenant.tenant_id == tenant_id)
        
        if not existing:
            # Create new tenant
            tenant = Tenant(
                tenant_id=tenant_id,
                name=tenant_config["name"],
                description=tenant_config.get("description", ""),
                is_active=True,
                settings=tenant_config.get("settings", {})
            )
            await tenant.insert()
            print(f"✅ Created tenant: {tenant_config['name']} ({tenant_id})")
        else:
            # Update existing tenant with latest config
            existing.name = tenant_config["name"]
            existing.description = tenant_config.get("description", "")
            existing.settings = tenant_config.get("settings", {})
            existing.is_active = True
            await existing.save()
            print(f"🔄 Updated tenant: {tenant_config['name']} ({tenant_id})")

