import functools
import pickle

import pytest

from just_jobs import RedisBroker

from .conftest import mock_func


@pytest.fixture(scope="session")
async def mock_broker():
    a = RedisBroker(url="redis://redis-storage", decode_responses=True)

    try:
        await a.startup()
        yield a, a.redis
    finally:
        await a.shutdown()


@pytest.mark.asyncio
async def test_enqueue(mock_broker):
    broker, redis = mock_broker
    jqueue = "jobqueue:test"
    pqueue = f"{jqueue}-processing"

    assert not await redis.llen(jqueue)
    assert not await redis.llen(pqueue)

    await broker.enqueue("test", b"hello world")

    assert await redis.llen(jqueue) == 1
    assert await redis.lpop(jqueue) == "hello world"
    assert not await redis.llen(pqueue)


@pytest.mark.asyncio
async def test_process_jobs(mock_broker):
    broker, redis = mock_broker
    jqueue = "jobqueue:test"
    pqueue = f"{jqueue}-processing"

    await redis.rpush(jqueue, pickle.dumps(functools.future(mock_func, "Hello")))

    ...
