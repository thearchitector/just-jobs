import functools
import pickle
from multiprocessing import Event, Process, synchronize
from typing import Callable, List, Optional, Tuple, Type

from .brokers import Broker, RedisBroker
from .errors import InvalidQueueException, NotReadyException


class Manager:
    def __init__(
        self,
        broker_class: Type[Broker] = RedisBroker,
        queue_names: Optional[List[str]] = None,
        *args,
        **kwargs,
    ):
        self.broker = broker_class(is_worker=False, *args, **kwargs)
        self.bargs = args
        self.bkwargs = kwargs

        self.queue_names = queue_names or ["default"]
        self.processes: List[Tuple[synchronize.Event, Process]] = []
        self._initialized = False

    async def __aenter__(self):
        await self.startup()
        return self

    async def startup(self):
        # allow the broker to startup whatever it needs
        await self.broker.startup()

        # spawn listening worker processes with communication pipes for cleanup
        for queue_name in self.queue_names:
            event = Event()
            p = Process(
                name=f"brokingworker-{queue_name}",
                target=self.broker._spawn_worker,
                args=(event, queue_name, *self.bargs),
                kwargs=self.bkwargs,
            )
            self.processes.append((event, p))
            p.start()

        self._initialized = True

    async def __aexit__(self, exc_type, exc, tb):
        await self.shutdown()

    async def shutdown(self):
        # shutdown the processes by setting their locking events rather than
        # sending a SIGTERM, to allow the workers to properly cleanup their resources
        # and connections.
        for event, process in self.processes:
            event.set()
            process.join()

        await self.broker.shutdown()

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
            raise ValueError("You need to enqueue a callable function.")

        # wrap in a partial for serialization
        partial = functools.partial(func, *args, **kwargs)
        serialized = pickle.dumps(partial)

        # request the storage broker dispatch the serialized job to the correct
        # worker thread
        return await self.broker.enqueue(queue_name, serialized)
