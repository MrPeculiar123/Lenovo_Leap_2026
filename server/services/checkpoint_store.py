"""Application lifecycle for the official LangGraph PostgreSQL checkpointer."""

import asyncio
import sys
from typing import Optional

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

try:
    from core.config import settings
except ImportError:
    from server.core.config import settings


_checkpointer: Optional[AsyncPostgresSaver] = None
_pool: Optional[AsyncConnectionPool] = None


if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def _psycopg_url() -> str:
    url = settings.DATABASE_URL

    for driver in ("+psycopg2", "+asyncpg", "+psycopg"):
        if url.startswith(f"postgresql{driver}://"):
            return "postgresql://" + url.split("://", 1)[1]

    return url


async def initialize_checkpointer() -> AsyncPostgresSaver:
    """Initialize the shared PostgreSQL connection pool and LangGraph checkpointer."""

    global _checkpointer, _pool

    if _checkpointer is not None:
        return _checkpointer

    _pool = AsyncConnectionPool(
        conninfo=_psycopg_url(),
        min_size=1,
        max_size=10,
        kwargs={
            "autocommit": True,
            "prepare_threshold": 0,
            "row_factory": dict_row,
        },
        open=False,
    )

    await _pool.open()

    try:
        _checkpointer = AsyncPostgresSaver(_pool)

        await _checkpointer.setup()

        return _checkpointer

    except BaseException:
        _checkpointer = None

        if _pool is not None:
            await _pool.close()

        _pool = None
        raise


async def close_checkpointer() -> None:
    """Close the PostgreSQL connection pool during application shutdown."""

    global _checkpointer, _pool

    _checkpointer = None

    if _pool is not None:
        await _pool.close()

    _pool = None


def get_checkpointer() -> AsyncPostgresSaver:
    if _checkpointer is None:
        raise RuntimeError(
            "LangGraph checkpointer has not been initialized"
        )

    return _checkpointer


async def checkpoint_state(thread_id: str) -> Optional[dict]:
    checkpoint = await get_checkpointer().aget(
        {
            "configurable": {
                "thread_id": thread_id
            }
        }
    )

    return checkpoint.get("channel_values") if checkpoint else None