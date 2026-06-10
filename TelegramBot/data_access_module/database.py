from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config import load_config

class Base(DeclarativeBase):
    pass

config = load_config()

engine = create_async_engine(
    config.database_url,
    echo=True,
)

async_session = async_sessionmaker(
    engine,
    expire_on_commit=False,
)

async def create_tables() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)