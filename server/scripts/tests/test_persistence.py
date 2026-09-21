import inspect

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver


def test_official_async_postgres_saver_is_available():
    context = AsyncPostgresSaver.from_conn_string("postgresql://invalid")
    assert hasattr(context, "__aenter__")
    assert hasattr(context, "__aexit__")
    assert inspect.iscoroutinefunction(AsyncPostgresSaver.setup)


def test_official_saver_exposes_async_checkpoint_operations():
    assert inspect.iscoroutinefunction(AsyncPostgresSaver.aget)
    assert inspect.iscoroutinefunction(AsyncPostgresSaver.aput)
    assert inspect.isasyncgenfunction(AsyncPostgresSaver.alist)
