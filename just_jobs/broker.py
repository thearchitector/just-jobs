from dataclasses import dataclass, field
from typing import Any, Callable, Dict

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings


@dataclass
class Broker:
    """
    Statically wraps `create_pool` to cache the the ArqRedis created by the
    specified settings and serialization functions. Provides an async context
    manager to the underlying connection pool.
    """

    redis_settings: RedisSettings
    packj: Callable[[Any], bytes] = field(repr=False)
    unpackj: Callable[[bytes], Any] = field(repr=False)
    kwargs: Dict

    _pool: ArqRedis = field(repr=False, init=False, default=None)

    async def pool(self):
        if not self._pool:
            self._pool = await create_pool(
                self.redis_settings,
                job_serializer=self.packj,
                job_deserializer=self.unpackj,
                **self.kwargs,
            )

        return self._pool

    def __await__(self):
        return self.pool().__await__()

    async def __aenter__(self):
        return await self.pool()

    async def __aexit__(self, *_):
        await self._pool.close(close_connection_pool=True)
