import asyncio

import pytest


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


def mock_func(message, person="banana"):
    return f"{message}, {person}"


async def mock_func_async(message, person="banana"):
    return f"{message}, {person}"


def mock_fail_func(message, person="oh noes"):
    raise RuntimeError("something isn't right")


async def mock_fail_func_async(message, person="oh noes"):
    raise RuntimeError("something isn't right")
