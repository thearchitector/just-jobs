import asyncio
import threading
from abc import ABC, abstractmethod
from multiprocessing.connection import Connection
from typing import Any


class Broker(ABC):
    def __init__(self, coroutines_per_worker: int = 20):
        self.coroutines_per_worker = coroutines_per_worker

    @abstractmethod
    async def setup(self, *args: Any, **kwargs: Any):
        """
        Performs any setup required by the storage broker, like connecting to a
        database.
        """
        raise NotImplementedError("Storage brokers must define a setup process.")

    @abstractmethod
    async def shutdown(self):
        """
        Performs any shutdown required by the broker, like ensuring disconnection from
        a database.
        """
        raise NotImplementedError("Storage brokers must define a shutdown process.")

    @abstractmethod
    async def enqueue(self, queue_name: str, job: bytes):
        raise NotImplementedError(
            "Storage brokers must define a way to enqueue serialized jobs."
        )

    def _spawn_workers(self, pipe: Connection, queue_name: str):
        loop = asyncio.new_event_loop()
        loop_thread = threading.Thread(target=loop.run_forever)

        # start the async thread and spawn N working coroutines
        loop_thread.start()
        for _ in range(self.coroutines_per_worker):
            asyncio.run_coroutine_threadsafe(self.process_job(queue_name), loop)

        # block until anything is sent through the pipe
        pipe.recv()

        # cleanup here
        loop.call_soon_threadsafe(loop.stop)
        loop_thread.join()
        loop.close()

    @abstractmethod
    async def process_job(self, queue_name: str):
        raise NotImplementedError(
            "Storage brokers must define a way to process queued jobs."
        )
