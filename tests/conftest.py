import os
from contextlib import redirect_stdout
from io import StringIO

import pytest
from arq.connections import RedisSettings
from arq.worker import create_worker

from just_jobs import BaseSettings


class Settings(metaclass=BaseSettings):
    redis_settings = RedisSettings(host=os.getenv("REDIS_HOST", "redis"))


@pytest.fixture(scope="session")
def settings():
    yield Settings


@pytest.fixture
async def pool(settings):
    async with settings.create_pool() as pool:
        yield pool


@pytest.fixture
def pcapture():
    yield redirect_stdout(StringIO())


@pytest.fixture
def enqueue_run_job(pool, settings, pcapture):
    async def runner(func, *args, **kwargs):
        job = await pool.enqueue_job(func.__name__, *args, **kwargs)

        worker = create_worker(
            settings_cls=settings,
            functions=[func],
            redis_pool=pool,
            burst=True,
            poll_delay=0,
        )
        with pcapture:
            await worker.main()
            await worker.close()

        return job

    return runner
