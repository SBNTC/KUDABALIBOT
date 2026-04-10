"""
Engine, session factory и init_db.
Импортируется всеми, кто работает с БД — но НЕ alembic/env.py.
"""
from sqlalchemy import event as _sa_event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool

from config import config
from database.models import Base

# SQLite не поддерживает concurrent writers — используем NullPool.
# Для PostgreSQL можно переключить на AsyncAdaptedQueuePool.
_is_sqlite = config.database_url.startswith("sqlite")
engine = create_async_engine(
    config.database_url,
    poolclass=NullPool if _is_sqlite else AsyncAdaptedQueuePool,
)
AsyncSessionMaker = async_sessionmaker(engine, expire_on_commit=False)


@_sa_event.listens_for(engine.sync_engine, "connect")
def _set_sqlite_pragmas(dbapi_conn, _record):
    """WAL mode + relaxed fsync для безопасной параллельной записи."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
