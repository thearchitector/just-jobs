from typing import Optional

from aioredis import ConnectionPool, Redis

from .base import Broker


class RedisBroker(Broker):
    def __init__(
        self,
        shutdown_with_pool: bool = True,
        url: Optional[str] = None,
        connection_pool: Optional[ConnectionPool] = None,
        **kwargs,
    ):
        super().__init__(coroutines_per_worker=kwargs.pop("coroutines_per_worker", 20))
        self.url = url
        self.connection_pool = connection_pool
        self.shutdown_with_pool = shutdown_with_pool
        self.rkwargs = kwargs

    async def startup(self):
        # creates a async redis instance by either a supplied connection pool or by url
        if self.connection_pool:
            self.redis = Redis(connection_pool=self.connection_pool, **self.rkwargs)
        else:
            self.redis = Redis.from_url(self.url, **self.rkwargs)
            self.connection_pool = self.redis.connection_pool

    async def shutdown(self):
        # shutdowns all redis connections
        await self.redis.close()
        if self.shutdown_with_pool:
            await self.connection_pool.disconnect()

    async def enqueue(self, queue_name: str, job: bytes):
        return await self.redis.rpush(f"jobqueue:{queue_name}", job)

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
                    await self.redis.lrem(pqueue, 0, serialized)
