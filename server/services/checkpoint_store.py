"""Application lifecycle for the official LangGraph PostgreSQL checkpointer."""

from contextlib import AbstractAsyncContextManager
import asyncio
import sys
from typing import Optional

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

try:
    from core.config import settings
except ImportError:
    from server.core.config import settings


_checkpointer: Optional[AsyncPostgresSaver] = None
_checkpointer_context: Optional[AbstractAsyncContextManager] = None

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def _psycopg_url() -> str:
    url = settings.DATABASE_URL
    for driver in ("+psycopg2", "+asyncpg", "+psycopg"):
        if url.startswith(f"postgresql{driver}://"):
            return "postgresql://" + url.split("://", 1)[1]
    return url


async def initialize_checkpointer() -> AsyncPostgresSaver:
    """Open the shared Psycopg 3 connection and initialize official tables once."""
    global _checkpointer, _checkpointer_context
    if _checkpointer is not None:
        return _checkpointer

    _checkpointer_context = AsyncPostgresSaver.from_conn_string(_psycopg_url())
    _checkpointer = await _checkpointer_context.__aenter__()
    try:
        await _checkpointer.setup()
    except BaseException:
        await _checkpointer_context.__aexit__(None, None, None)
        _checkpointer = None
        _checkpointer_context = None
        raise
    return _checkpointer


async def close_checkpointer() -> None:
    """Close the shared checkpointer connection during application shutdown."""
    global _checkpointer, _checkpointer_context
    if _checkpointer_context is not None:
        await _checkpointer_context.__aexit__(None, None, None)
    _checkpointer = None
    _checkpointer_context = None


def get_checkpointer() -> AsyncPostgresSaver:
    if _checkpointer is None:
        raise RuntimeError("LangGraph checkpointer has not been initialized")
    return _checkpointer


async def checkpoint_state(thread_id: str) -> Optional[dict]:
    checkpoint = await get_checkpointer().aget({"configurable": {"thread_id": thread_id}})
    return checkpoint.get("channel_values") if checkpoint else None
