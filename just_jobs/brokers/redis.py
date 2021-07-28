import asyncio
import pickle
from typing import Any

import aioredis

from .base import Broker


class RedisBroker(Broker):
    async def setup(self, *args: Any, **kwargs: Any):
        # creates a async redis instance by either a supplied connection pool or by url
        connection_pool: aioredis.ConnectionPool = kwargs.pop("connection_pool", None)
        self.connection_pool = connection_pool
        if connection_pool:
            self.redis = aioredis.Redis(connection_pool=connection_pool)
        else:
            self.redis = aioredis.Redis.from_url(kwargs.pop("url"), **kwargs)

    async def shutdown(self, *args: Any, **kwargs: Any):
        # shutdowns all redis connections
        await self.redis.close()
        if self.connection_pool:
            await self.connection_pool.disconnect()

    async def enqueue(self, queue_name: str, job: bytes):
        return await self.redis.rpush(f"jobqueue:{queue_name}", job)

    async def process_job(self, queue_name: str):
        jqueue = f"jobqueue:{queue_name}"
        pqueue = f"{jqueue}-processing"
        loop = asyncio.get_running_loop()

        while True:
            # deserialize the queued job for processing
            serialized = await self.redis.brpoplpush(jqueue, pqueue, timeout=30)

            if serialized:
                partial = pickle.loads(serialized)

                # run the job as a coroutine or in a threadpool
                if asyncio.iscoroutinefunction(partial.func):
                    await partial()
                else:
                    await loop.run_in_executor(None, partial)

                # remove from the processing queue
                await self.redis.lrem(pqueue, 0, serialized)
