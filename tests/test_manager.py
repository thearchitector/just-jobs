import pickle
from unittest.mock import MagicMock

import pytest

from just_jobs import Broker, Manager, errors

from .conftest import mock_func


class MockBroker(Broker):
    async def startup(self):
        pass

    async def shutdown(self):
        pass

    async def enqueue(self, queue_name: str, job: bytes):
        return queue_name, job

    async def process_jobs(self, queue_name: str):
        pass


@pytest.fixture
def stop_multiprocessing(monkeypatch):
    event_mock, process_mock = MagicMock(), MagicMock()
    event_mock.return_value, process_mock.return_value = event_mock, process_mock
    monkeypatch.setattr("just_jobs.manager.Event", event_mock)
    monkeypatch.setattr("just_jobs.manager.Process", process_mock)
    return event_mock, process_mock


@pytest.mark.asyncio
async def test_not_initialized():
    def test(message, person="banana"):
        return f"{message} - {person}"

    m = Manager()
    with pytest.raises(errors.NotReadyException):
        await m.enqueue(test, "Hello", person="Elias")


@pytest.mark.asyncio
async def test_startup_shutdown(stop_multiprocessing):
    event_mock, process_mock = stop_multiprocessing
    async with Manager(broker=MockBroker) as m:
        assert m.processes
        event_mock.assert_called()
        process_mock.start.assert_called()

    event_mock.set.assert_called()
    process_mock.join.assert_called()


@pytest.mark.asyncio
async def test_bad_queue(stop_multiprocessing):
    async with Manager(broker=MockBroker) as m:
        with pytest.raises(errors.InvalidQueueException):
            await m.enqueue(mock_func, "Hello", queue_name="banana", person="Elias")


@pytest.mark.asyncio
async def test_enqueue(stop_multiprocessing):
    async with Manager(broker=MockBroker) as m:
        queue_name, serialized = await m.enqueue(mock_func, "Hello", person="Elias")
        assert queue_name == "default"
        func = pickle.loads(serialized)
        assert func() == "Hello, Elias"
