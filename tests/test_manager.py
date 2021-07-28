import pickle

import pytest

from just_jobs import Manager, errors

from .conftest import MockBroker


@pytest.mark.asyncio
async def test_not_initialized():
    def test(message, person="banana"):
        return f"{message} - {person}"

    m = Manager()
    with pytest.raises(errors.NotReadyException):
        await m.enqueue(test, "Hello", person="Elias")


def mock_func(message, person="banana"):
    return f"{message}, {person}"


@pytest.mark.asyncio
async def test_bad_queue():
    async with Manager(broker_class=MockBroker) as m:
        with pytest.raises(errors.InvalidQueueException):
            await m.enqueue(mock_func, "Hello", queue_name="banana", person="Elias")


@pytest.mark.asyncio
async def test_enqueue():
    async with Manager(broker_class=MockBroker) as m:
        queue_name, serialized = await m.enqueue(mock_func, "Hello", person="Elias")
        assert queue_name == "default"
        func = pickle.loads(serialized)
        assert func() == "Hello, Elias"
