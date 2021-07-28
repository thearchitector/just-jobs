import asyncio

import pytest

from just_jobs import Broker


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


class MockBroker(Broker):
    async def setup(self, *args, **kwargs):
        pass

    async def shutdown(self):
        pass

    async def enqueue(self, queue_name: str, job: bytes):
        return queue_name, job

    async def process_job(self, queue_name: str):
        pass
