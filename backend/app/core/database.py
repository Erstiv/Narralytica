from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.core.config import settings

# Convert postgresql:// to postgresql+asyncpg://
async_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(async_url, echo=settings.environment == "development")
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Alias for background tasks that need their own session
async_session_factory = async_session


async def get_db():
    async with async_session() as session:
        yield session
