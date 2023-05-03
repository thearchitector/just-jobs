from asyncio import Future
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_create_pool():
    awaitable = Future()
    mock = MagicMock(side_effect=lambda **kwargs: awaitable)
    mock.close = mock
    awaitable.set_result(mock)

    with patch(
        "just_jobs.broker.create_pool", new=MagicMock(return_value=awaitable)
    ) as create_pool:
        yield create_pool


async def test_create(settings, mock_create_pool):
    broker = settings.create_pool()
    await broker  # __await__
    await broker
    mock_create_pool.assert_called_once()


async def test_contextmanager(settings, mock_create_pool):
    broker = settings.create_pool()

    async with broker:  # __aenter__
        async with broker as pool:
            pass

    mock_create_pool.assert_called_once()
    pool.close.assert_called()
