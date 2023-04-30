import asyncio
from typing import Optional

from arq.connections import RedisSettings

from just_jobs import BaseSettings, Context, JobType, job


@job()
async def async_task(ctx: Context, url: str):
    print("async!", url)
    return url


@job(job_type=JobType.IO_BOUND)
def sync_task(ctx: Optional[Context], url: str):
    # if the context is present, this is being run from the arq listener
    if ctx:
        print("sync!", url)
    return url


class Settings(metaclass=BaseSettings):
    functions = [async_task, sync_task]
    redis_settings = RedisSettings(host="redis")


async def main():
    # create a redis broker using the Settings already defined
    broker = await Settings.create_broker()
    # run the_task right now and return the url
    # even though this is a sync function, `.now` returns an awaitable
    url = await sync_task.now("https://www.google.com")
    print(url)

    await broker.enqueue_job("async_task", "https://gianturl.net")
    await broker.enqueue_job("sync_task", "https://gianturl.net")


if __name__ == "__main__":
    asyncio.run(main())
