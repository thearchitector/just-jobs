import functools
import pickle

import pytest
from redis.asyncio import Redis

from just_jobs import RedisBroker

from .conftest import mock_fail_func, mock_fail_func_async, mock_func, mock_func_async


@pytest.fixture(scope="session")
async def mock_broker(event_loop):
    a = RedisBroker(url="redis://redis-storage")
    a.is_worker = True
    a.loop = event_loop

    try:
        await a.startup()
        yield a, a.redis
    finally:
        await a.redis.flushdb()
        await a.shutdown()


class LoopExitRedis(Redis):
    def lrem(self, name, count, value):
        async def wrapper():
            await super(LoopExitRedis, self).lrem(name, count, value)
            raise Exception("loop interrupt")

        return wrapper()


@pytest.mark.asyncio
async def test_run_coro_job_bad(mock_broker):
    broker, _ = mock_broker
    f = pickle.dumps(functools.partial(mock_fail_func_async, "Hello"))
    res = await broker.run_job(f)
    assert not res


@pytest.mark.asyncio
async def test_run_job_bad(mock_broker):
    broker, _ = mock_broker
    f = pickle.dumps(functools.partial(mock_fail_func, "Hello"))
    res = await broker.run_job(f)
    assert not res


@pytest.mark.asyncio
async def test_run_coro_job(mock_broker):
    broker, _ = mock_broker
    f = pickle.dumps(functools.partial(mock_func_async, "Hello"))
    res = await broker.run_job(f)
    assert res is True


@pytest.mark.asyncio
async def test_run_job(mock_broker):
    broker, _ = mock_broker
    f = pickle.dumps(functools.partial(mock_func, "Hello"))
    res = await broker.run_job(f)
    assert res is True


@pytest.mark.asyncio
async def test_enqueue(mock_broker):
    broker, redis = mock_broker
    jqueue = "jobqueue:test"
    pqueue = f"{jqueue}-processing"

    assert not await redis.llen(jqueue)
    assert not await redis.llen(pqueue)

    await broker.enqueue("test", b"hello world")

    assert await redis.llen(jqueue) == 1
    assert await redis.lpop(jqueue) == b"hello world"
    assert not await redis.llen(pqueue)


@pytest.mark.asyncio
async def test_process_jobs_good(mock_broker):
    broker, _ = mock_broker
    broker.redis = LoopExitRedis.from_url("redis://redis-storage")
    redis = broker.redis
    broker.connection_pool = redis.connection_pool
    jqueue = "jobqueue:test"
    pqueue = f"{jqueue}-processing"

    await redis.rpush(jqueue, pickle.dumps(functools.partial(mock_func, "Hello")))

    with pytest.raises(Exception, match="loop interrupt"):
        await broker.process_jobs("test")

    assert not await redis.llen(jqueue)
    assert not await redis.llen(pqueue)
