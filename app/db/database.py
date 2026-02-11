"""
Database Connection
===================
Async PostgreSQL connection using SQLAlchemy
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker


# Connection string - will come from environment variables later
DATABASE_URL = "postgresql+asyncpg://outbound:outbound@localhost:5432/outbound"

# Create engine
engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # Set to False in production
    future=True,
)

# Session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session():
    """Get a database session"""
    async with async_session_factory() as session:
        yield session


async def init_db():
    """Create all tables (for development only - use Alembic in production)"""
    from models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database tables created")