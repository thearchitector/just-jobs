import asyncio
import pickle
import threading
from abc import ABC, abstractmethod
from multiprocessing.synchronize import Event


class Broker(ABC):
    def __init__(self, *args, **kwargs):
        # settings
        self.coroutines_per_worker = kwargs.pop("coroutines_per_worker", 20)

        # operational
        self.is_worker = kwargs.pop("is_worker", False)
        self.loop = kwargs.pop("event_loop", None)

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
        Performs any shutdown required by the broker, like ensuring disconnection from
        a database.
        """
        raise NotImplementedError("Storage brokers must define a shutdown process.")

    @abstractmethod
    async def enqueue(self, queue_name: str, job: bytes):
        raise NotImplementedError(
            "Storage brokers must define a way to enqueue serialized jobs."
        )

    @abstractmethod
    async def process_jobs(self, queue_name: str):
        raise NotImplementedError(
            "Storage brokers must define a way to process queued jobs."
        )

    @classmethod
    def _spawn_worker(cls, event: Event, queue_name: str, *bargs, **bkwargs):
        loop = asyncio.new_event_loop()
        loop_thread = threading.Thread(target=loop.run_forever)
        loop_thread.start()

        # create worker and wait for it to startup
        worker = cls(*bargs, is_worker=True, event_loop=loop, **bkwargs)
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

    async def run_job(self, job: bytes) -> bool:
        """
        Loads and executes a job, either directly in the event loop if it's a
        coroutine or in a threadpool if it isn't. Returns if the job ran successfully
        or not.
        """
        partial = pickle.loads(job)

        try:
            # run the job as a coroutine or in a threadpool
            if asyncio.iscoroutinefunction(partial.func):
                await partial()
            else:
                await self.loop.run_in_executor(None, partial)

            return True
        except Exception:
            # TODO: what happens when a job fails? probably should keep track
            # somewhere with a retry counter instead of leaving it pending
            return False
