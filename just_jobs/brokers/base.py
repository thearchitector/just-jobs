import asyncio
import pickle
import threading
from abc import ABC, abstractmethod
from multiprocessing.synchronize import Event
from typing import Optional


class Broker(ABC):
    """
    An abtract Broker interface used to define custom functionality. Every
    Broker class must inherit from this interface and override the defined
    abstract methods.
    """

    def __init__(self, coroutines_per_worker: int = 20):
        # settings
        self.coroutines_per_worker = coroutines_per_worker
        """
        The number of coroutine working tasks to spawn per queue. Each coroutine
        processes and runs jobs atomically, and their parallelism is handeled by
        asyncio. Defaults to 20.
        """

        # operational
        self.is_worker: bool = False
        """
        Set by the `Manager` to mark this broker as a worker responsible for
        processing jobs. May be used during startup and shutdown to do
        worker-specific actions.
        """
        self.loop: Optional[asyncio.AbstractEventLoop] = None

    @abstractmethod
    async def startup(self):
        """
        Performs any setup required by the storage broker, like connecting to a
        database.
        """
        raise NotImplementedError("Storage brokers must define a startup process.")

    @abstractmethod
    async def shutdown(self):
        """
        Performs any shutdown required by the broker, like ensuring
        disconnection from a database.
        """
        raise NotImplementedError("Storage brokers must define a shutdown process.")

    @abstractmethod
    async def enqueue(self, queue_name: str, job: bytes):
        """
        Enqueues the given serialized job to the provided queue for later
        processing.
        """
        raise NotImplementedError(
            "Storage brokers must define a way to enqueue serialized jobs."
        )

    @abstractmethod
    async def process_jobs(self, queue_name: str):
        """
        Infinitly polls for new jobs pushed the given queue and attempts to run
        them via `Broker.run_job`. Jobs must be dequeued atomically. This
        method is also responsible for determining what to do if a job fails,
        like re-adding it to the queue.

        ~ See `RedisBroker.process_jobs` for an example.
        """
        raise NotImplementedError(
            "Storage brokers must define a way to process queued jobs. "
            "This should run forever."
        )

    async def run_job(self, job: bytes) -> bool:
        """
        Loads and executes a job, either directly in the event loop if it's a
        coroutine or in a threadpool if it isn't. Returns if the job ran
        successfully or not.
        """
        partial = pickle.loads(job)

        try:
            # run the job as a coroutine or in a threadpool
            if asyncio.iscoroutinefunction(partial.func):
                await partial()
            elif self.loop:
                await self.loop.run_in_executor(None, partial)

            return True
        except Exception:
            # TODO: what happens when a job fails? probably should keep track
            # somewhere with a retry counter instead of leaving it pending
            return False

    @classmethod
    def _spawn_worker(cls, event: Event, queue_name: str, **kwargs):
        loop = asyncio.new_event_loop()
        loop_thread = threading.Thread(target=loop.run_forever)
        loop_thread.start()

        # create worker and wait for it to startup
        worker = cls(**kwargs)
        worker.is_worker = True
        worker.loop = loop
        asyncio.run_coroutine_threadsafe(worker.startup(), loop).result()

        # spawn N working coroutines
        futs = [
            asyncio.run_coroutine_threadsafe(worker.process_jobs(queue_name), loop)
            for _ in range(worker.coroutines_per_worker)
        ]

        # block until the shutdown event is set
        event.wait()

        # cancel all worker coroutines
        for fut in futs:
            loop.call_soon_threadsafe(fut.cancel)

        # wait for the worker shutdown to complete
        asyncio.run_coroutine_threadsafe(worker.shutdown(), loop).result()

        # cleanup the loop
        loop.call_soon_threadsafe(loop.stop)
        loop_thread.join()
        loop.close()
