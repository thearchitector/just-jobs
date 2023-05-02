from contextlib import redirect_stdout
from io import StringIO

import pytest
from arq.connections import RedisSettings

from just_jobs import BaseSettings


class Settings(metaclass=BaseSettings):
    redis_settings = RedisSettings(host="redis")


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
