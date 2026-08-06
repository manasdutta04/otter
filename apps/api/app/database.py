import asyncio
import weakref
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from .config import get_settings

class Base(DeclarativeBase):
    pass

_engine_cache: weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, object] = weakref.WeakKeyDictionary()


def get_engine():
    loop = asyncio.get_running_loop()
    if loop not in _engine_cache:
        _engine_cache[loop] = create_async_engine(get_settings().database_url, pool_pre_ping=True)
    return _engine_cache[loop]


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with get_session_factory()() as session:
        yield session
