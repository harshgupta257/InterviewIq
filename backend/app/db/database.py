"""Async SQLAlchemy engine and session factory."""

from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings


def build_engine(settings: Settings) -> AsyncEngine:
    kwargs: dict[str, Any] = {"pool_pre_ping": True}
    if settings.is_sqlite:
        kwargs = {"connect_args": {"check_same_thread": False}}
    else:
        # Disable asyncpg's statement cache so the Supabase transaction pooler
        # (pgbouncer, port 6543) works; harmless with the session pooler.
        kwargs["connect_args"] = {"statement_cache_size": 0, "command_timeout": 30}
        kwargs["pool_size"] = 5
        kwargs["max_overflow"] = 5
    engine = create_async_engine(settings.database_url, **kwargs)

    if settings.is_sqlite:
        # SQLite needs foreign keys switched on per connection for ON DELETE CASCADE.
        @event.listens_for(engine.sync_engine, "connect")
        def _fk_pragma(dbapi_conn: Any, _: Any) -> None:
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def build_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def session_scope(factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncSession]:
    async with factory() as session:
        yield session
