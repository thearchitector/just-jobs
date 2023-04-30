# just-jobs

![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/thearchitector/just-jobs/ci.yaml?label=tests&style=flat-square)
![PyPI - Downloads](https://img.shields.io/pypi/dw/just-jobs?style=flat-square)
![GitHub](https://img.shields.io/github/license/thearchitector/just-jobs?style=flat-square)
[![Buy a tree](https://img.shields.io/badge/Treeware-%F0%9F%8C%B3-lightgreen?style=flat-square)](https://ecologi.com/eliasgabriel?r=6128126916bfab8bd051026c)

A friendly and lightweight wrapper for [arq](https://arq-docs.helpmanual.io). just-jobs provides a simple interface on top of arq that implements additional functionality like synchronous job types (IO-bound vs. CPU-bound) and signed and secure task serialization.

Documentation: <https://justjobs.thearchitector.dev>.

```sh
$ pdm add just-jobs # or
$ pip install --user just-jobs
```

## Features

just-jobs doesn't aim to replace the invocations that arq provides, only wrap some of them to make job creation and execution easier and better. It lets you:

- Define and run non-async jobs. Passing a non-async `@job` function to arq will run properly. Non-async jobs can also be defined as either IO-bound or CPU-bound, which changes how the job will be executed to prevent blocking the asyncio event loop.
- Specify a single `RedisSettings` within your `WorkerSettings` which you can create a pool from with `Settings.create_broker()`.
- Run jobs either immediately with the `.now()` function or via normal arq enqueueing.
- Use non-pickable job arguments and kwargs through the [dill](http://dill.rtfd.io/) library.

Because the aim is simplicity, just-jobs makes some opinionated design decisions. Namely:

- If defining a sync job, you must declare it as either `IO_BOUND` or `CPU_BOUND` so just-jobs knows how to optimally run it. This helps ensure that the arq process event loop is never blocked while encouraging thoughtful and intentional job design.
- You cannot override the job serialization logic or lifecycle hooks of `BaseSettings`. Jobs are serialized using dill (to support a wider range of arguments) and are always signed for security.

## Usage

Using just-jobs is pretty straight forward:

1. Adding `@job()` to any function will turn it into job that can be delayed by `arq`.

2. If the job is sync, specify it's type like `@job(job_type=JobType.IO_BOUND)`.

3. If you only want to write one function but need to occasionally invoke it immediately, use `yourjob.now(...)`.

4. Create your worker settings by specifying `metaclass=BaseSettings` to your settings class.

### Example

```py
from just_jobs import BaseSettings, Context, JobType, job

@job()
async def async_task(ctx: Context, url: str):
    return url

@job(job_type=JobType.IO_BOUND)
def sync_task(ctx: Optional[Context], url: str):
    # if the context is present, this is being run from the arq listener
    if ctx:
        print(url)
    return url

class Settings(metaclass=BaseSettings):
    functions = [async_task, sync_task]
    redis_settings = RedisSettings(host="redis")

async def main():
    # create a redis broker using the Settings already defined
    broker = await Settings.create_broker()
    # run the_task right now and return the url
    url = await sync_task.now("https://www.google.com")

    await broker.enqueue_job("the_task", "https://gianturl.net")
```

## License

This software is licensed under the [BSD 2-Clause “Simplified” License](LICENSE).

This package is [Treeware](https://treeware.earth). If you use it in production, consider [**buying the world a tree**](https://ecologi.com/eliasgabriel?r=6128126916bfab8bd051026c) to thank me for my work. By contributing to my forest, you’ll be creating employment for local families and restoring wildlife habitats.
