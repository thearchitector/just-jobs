from typing import Optional

from redis.asyncio import ConnectionPool, Redis

from .base import Broker


class RedisBroker(Broker):
    """
    Production-ready job broker using redis-py for queue management
    and job persistence.
    """

    def __init__(
        self,
        shutdown_with_pool: bool = True,
        url: Optional[str] = None,
        connection_pool: Optional[ConnectionPool] = None,
        **kwargs,
    ):
        super().__init__(coroutines_per_worker=kwargs.pop("coroutines_per_worker", 20))
        self.url = url
        """
        A valid fully-qualified URL to a Redis instance, of one of the following
        formats. Mutually exclusive with `connection_pool`.

        ```plain
        redis://[[username]:[password]]@localhost:6379/0
        rediss://[[username]:[password]]@localhost:6379/0
        unix://[[username]:[password]]@/path/to/socket.sock?db=0
        ```
        """
        self.connection_pool = connection_pool
        """
        A valid connection pool to a Redis instance.
        """
        self.shutdown_with_pool = shutdown_with_pool
        """
        Indicates that the connection pool should release all connections and
        disconnect when the broker is shutdown. Defaults to true.
        """
        self.kwargs = kwargs
        """
        Any keyword arguments to pass through to the Redis instance during
        creation.
        """

    async def startup(self):
        # creates a async redis instance by either a supplied connection pool or by url
        if self.connection_pool:
            self.redis: Redis = Redis(
                connection_pool=self.connection_pool, **self.kwargs
            )
        elif self.url:
            self.redis: Redis = Redis.from_url(self.url, **self.kwargs)  # type: ignore
            self.connection_pool = self.redis.connection_pool
        else:
            raise ValueError(
                "You must specify either a valid Redis URL or existing connection pool!"
            )

    async def shutdown(self):
        # shutdowns all redis connections
        await self.redis.close()
        if self.connection_pool and self.shutdown_with_pool:
            await self.connection_pool.disconnect()

    async def enqueue(self, queue_name: str, job: bytes):
        return await self.redis.rpush(f"jobqueue:{queue_name}", job)  # type: ignore

    async def process_jobs(self, queue_name: str):
        jqueue = f"jobqueue:{queue_name}"
        pqueue = f"{jqueue}-processing"

        while True:
            # deserialize the queued job for processing
            serialized = await self.redis.brpoplpush(jqueue, pqueue, timeout=5)

            if serialized:
                # run the job
                successful = await super().run_job(serialized)
                if successful:
                    # remove from the processing queue
                    await self.redis.lrem(pqueue, 0, serialized)  # type: ignore
