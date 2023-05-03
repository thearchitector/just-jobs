import asyncio

from arq.connections import RedisSettings

from just_jobs import BaseSettings, JobType, job
from just_jobs.typing import Context


@job()
async def async_task(url: str) -> str:
    print("async!", url)
    return url


@job(job_type=JobType.CPU_BOUND)
def sync_task(ctx: Context, url: str) -> str:
    # if the context is present, this is being run from the arq listener
    if ctx:
        print("sync!", url)
    return url


class Settings(metaclass=BaseSettings):
    functions = [async_task, sync_task]
    redis_settings = RedisSettings(host="redis")


async def main() -> None:
    # create a redis broker using the Settings already defined
    async with Settings.create_pool() as pool:
        # run the_task right now and return the url
        # even though this is a sync function, `.now` returns an awaitable
        url = await sync_task.now("https://www.google.com")
        print(url)

        await pool.enqueue_job("async_task", "https://gianturl.net")
        await pool.enqueue_job("sync_task", "https://gianturl.net")


if __name__ == "__main__":
    # run me, then run `arq docs.example.Settings`
    asyncio.run(main())
