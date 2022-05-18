"""The entrypoint for all job queueing and brokering within an application."""

import functools
import pickle
from multiprocessing import Event, Process
from typing import Callable, List, Optional, Type

from .brokers import Broker, RedisBroker
from .errors import InvalidEnqueueableFunction, InvalidQueueException, NotReadyException


class Manager:
    """The entrypoint for all job queueing and brokering within an application."""

    def __init__(
        self,
        broker: Type[Broker] = RedisBroker,
        queue_names: Optional[List[str]] = None,
        **bkwargs,
    ):
        self.queue_names = queue_names or ["default"]
        """
        The queue names to which jobs will be placed.

        It is ***highly*** recommended to set this list of queue names to
        logically / functionally separate action-flows in your application.
        This is because jobs in a single queue are processed sequentially
        (albeit in asyncio-parallel). Defining separate queues for unrelated
        actions ensures that a job in one queue does not block the unrelated
        job from executing.
        """

        self.broker = broker(**bkwargs)
        """
        The broker class to instantiate. `RedisBroker` by default, but may be
        replaced with a custom `Broker` if desired.
        """
        self.bkwargs = bkwargs
        """
        Any keyword arguments to pass to the `broker` during initialization."""

        self.processes: List[Process] = []
        self._initialized = False

    async def startup(self):
        """
        Startup the broker to allow it to perform any initial actions, like connecting
        to a database. Also spawn/fork the processing queues and register them
        with the manager, to allow for graceful cleanup during shutdown.
        """
        # allow the broker to startup whatever it needs
        await self.broker.startup()

        # spawn listening worker processes with communication events for cleanup
        self._pevent = Event()
        for queue_name in self.queue_names:
            p = Process(
                name=f"brokingworker-{queue_name}",
                target=self.broker._spawn_worker,
                args=(self._pevent, queue_name),
                kwargs=self.bkwargs,
            )
            self.processes.append(p)
            p.start()

        self._initialized = True

    async def shutdown(self):
        """
        Signal all processing workers to shutdown and wait for them to cleanup. Also
        gracefully shutdown the broker. This must be called after startup.
        """
        if not self._initialized:
            raise NotReadyException()

        # shutdown the processes by setting their locking events rather than
        # sending a SIGTERM, to allow the workers to properly cleanup their resources
        # and connections.
        self._pevent.set()
        for process in self.processes:
            process.join()

        await self.broker.shutdown()
        self._initialized = False

    async def enqueue(
        self, func: Callable, *args, queue_name: str = "default", **kwargs
    ):
        """
        Enqueues the given function and its arguments for asynchronous execution
        sometime in the near future. All functions are wrapped and serialized. No
        guarantee is given for WHEN an enqueued job will be run, only that it will
        (or at least, attempted). The time until execution will depend on the number
        of enqueued tasks, their complexities, and the rest of the workload present on
        the system.
        """
        if not self._initialized:
            raise NotReadyException()
        elif queue_name not in self.queue_names:
            raise InvalidQueueException()
        elif not callable(func):
            raise InvalidEnqueueableFunction()

        # wrap in a partial for serialization
        partial = functools.partial(func, *args, **kwargs)
        serialized = pickle.dumps(partial)

        # request the storage broker dispatch the serialized job to the correct
        # worker thread
        return await self.broker.enqueue(queue_name, serialized)

    async def __aenter__(self):
        await self.startup()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.shutdown()
