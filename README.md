# just-jobs

![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/thearchitector/just-jobs/ci.yaml?label=tests&style=flat-square)
![PyPI - Downloads](https://img.shields.io/pypi/dw/just-jobs?style=flat-square)
![GitHub](https://img.shields.io/github/license/thearchitector/just-jobs?style=flat-square)
[![Buy a tree](https://img.shields.io/badge/Treeware-%F0%9F%8C%B3-lightgreen?style=flat-square)](https://ecologi.com/eliasgabriel?r=6128126916bfab8bd051026c)

A friendly and lightweight wrapper for [arq](https://arq-docs.helpmanual.io). just-jobs provides a simple interface on top of arq that implements additional functionality like synchronous job types (IO-bound vs. CPU-bound) and signed and secure task serialization.

Documentation: <https://justjobs.thearchitector.dev>.

Tested support on Python 3.7, 3.8, 3.9, and 3.10, 3.11.

```sh
$ pdm add just-jobs
# or
$ pip install --user just-jobs
```

## Features

just-jobs doesn't aim to replace the invocations that arq provides, only wrap some of them to make job creation and execution easier and better. It lets you:

- Define and run non-async jobs. Passing a non-async `@job` function to arq will run properly. Non-async jobs can also be defined as either IO-bound or CPU-bound, which changes how the job will be executed to prevent blocking the asyncio event loop.
- The arq `Context` parameter now works a lot like [FastAPI's `Request`](https://fastapi.tiangolo.com/advanced/using-request-directly/). It's no longer a required parameter, but if it exists it will get set. It doesn't have to be named `ctx` either, only have the type `Context`.
- Specify a single `RedisSettings` within your `WorkerSettings` from which you can create a pool using `Settings.create_pool()`.
- Run jobs either immediately with the `.now()` function or via normal arq enqueueing.
- Use non-pickable job arguments and kwargs (supported by the [dill](http://dill.rtfd.io/) library).

## Usage

Using just-jobs is pretty straight forward.

### Add `@job()` to any function to make it a delayable job.

If the job is synchronous, specify its job type so just-jobs knows how to optimally run it. If you don't, you'll get an error. This helps encourage thoughtful and intentional job design while ensuring that the event loop is never blocked.

```python
@job(job_type=JobType.CPU_BOUND)
def complex_math(i: int, j: int, k: int)
```

If it's a coroutine function, you don't need to specify a job type (and will get a warning if you do). This might change in the future to support asynchronous CPU-bound tasks.

```python
@job()
async def poll_reddit(ctx: Context, subr: str)
    if ctx:
        # enqueued then run by arq
    else:
        # invoked manually
```

`@job` works similarly to `arq.func()`. If can pass in variables such as `keep_result` and `max_tries` to configure the same behavior.

### Use `.now` if you want to run the job immediately.

Using `.now` allows you to run the job as if it were a normal function. If you have logic that you only want to execute when enqueued, include a parameter with type `Context` and check if it exists at runtime (functions with a `Context` that are run immediately will have that argument set to `None`).

```python
await complex_math.now(1, 1, 2)
await poll_reddit.now("r/Python")
```

### Define WorkerSettings using the `BaseSettings` metaclass.

The execution logic that `@job` provides requires some stuff. When you defining your WorkerSettings, you must declare `BaseSettings` as its metaclass to ensure that stuff exists.

```python
class Settings(metaclass=BaseSettings):
    redis_settings = ...
```

### Use `Settings.create_pool()`.

While you may elect to use `arq.connections.create_pool` as you would normally, using the `create_pool` function provided by your `Settings` class ensures the pool it creates always matches your worker's Redis settings. It also lets you take advantage of additional functionality, namely that it can be used as an auto-closing context manager.

```python
# manually
pool = await Settings.create_pool()
await pool.close(close_connection_pool=True)

# or as an async context manager
async with Settings.create_pool() as pool:
    ...
```

### Enqueue your job.

just-jobs doesn't change the way in which you enqueue your jobs. Just use `await pool.enqueue_job(...)`.

```python
await pool.enqueue_job('complex_math', 2, 1, 3)
```

## Caveats

`arq.func()` and `@job()` are mutually exclusive. If you want to configure a job in the same way, pass the settings you would have passed to `func()` to `@job()` instead. Passing an `@job()` to `func()` will **not** edit its configuration.

```python
@job(job_type=JobType.CPU_BOUND, keep_result_forever=True, max_tries=10)
def task(a: int, b: int):
    return a + b
```

## Example

The complete example is available at [docs/example.py](docs/example.py) and should work out of the box. The snippet below is just an excerpt to show the features described above:

```python
from just_jobs import BaseSettings, Context, JobType, job

@job()
async def async_task(url: str):
    return url

@job(job_type=JobType.IO_BOUND)
def sync_task(ctx: Context, url: str):
    # if the context is present, this is being run from the arq listener
    if ctx:
        print(url)
    return url

class Settings(metaclass=BaseSettings):
    functions = [async_task, sync_task]
    redis_settings = RedisSettings(host="redis")

async def main():
    # create a Redis pool using the Settings already defined
    pool = await Settings.create_pool()
    # run the_task right now and return the url
    # even though this is a sync function, `.now` returns an awaitable
    url = await sync_task.now("https://www.theglassfiles.com")

    await pool.enqueue_job("async_task", "https://www.eliasfgabriel.com")
    await pool.enqueue_job("sync_task", "https://gianturl.net")

    await pool.close(close_connection_pool=True)
```

## License

This software is licensed under the [BSD 2-Clause “Simplified” License](LICENSE).

This package is [Treeware](https://treeware.earth). If you use it in production, consider [**buying the world a tree**](https://ecologi.com/eliasgabriel?r=6128126916bfab8bd051026c) to thank me for my work. By contributing to my forest, you’ll be creating employment for local families and restoring wildlife habitats.

```

```
