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

just-jobs doesn't aim to replace the invocations that arq provides, only wrap some of them to make job creation and execution better and easier. It lets you:

- Define and run non-async jobs. Passing a non-async `@job` function to arq will run properly. Non-async jobs can also be defined as either IO-bound or CPU-bound, which changes how the job will be executed to prevent blocking the asyncio event loop.
- The arq `Context` parameter now works a lot like [FastAPI's `Request`](https://fastapi.tiangolo.com/advanced/using-request-directly/). It's no longer a required parameter, but if it exists, it will get set. It doesn't have to be named `ctx` either, only have the type `Context`.
- Specify a single `RedisSettings` within your `WorkerSettings` from which you can create a pool using `Settings.create_pool()`.
- Run jobs either immediately or via normal arq enqueueing.
- Use non-picklable job arguments and kwargs (supported by the [dill](http://dill.rtfd.io/) library).
- Signed secure job serialization using `blake2b`.

## Usage

Using just-jobs is pretty straight forward:

### Add `@job()` to any function to make it a delayable job.

If the job is synchronous, specify its job type so just-jobs knows how to optimally run it. If you don't, you'll get an error. This helps encourage thoughtful and intentional job design while ensuring that the event loop is never blocked.

```python
@job(job_type=JobType.CPU_BOUND) # or JobType.IO_BOUND
def complex_math(i: int, j: int, k: int)
```

If it's a coroutine function, you don't need to specify a job type (and will get a warning if you do).

```python
@job()
async def poll_reddit(subr: str)
```

By default, just-jobs will utilize your Python version's default number of [thread](https://docs.python.org/3/library/concurrent.futures.html#concurrent.futures.ThreadPoolExecutor) and [process](https://docs.python.org/3/library/concurrent.futures.html#concurrent.futures.ProcessPoolExecutor) workers to handle IO-bound and CPU-bound tasks respectively. On 3.8+, that is `min(32, CPU_COUNT + 4)` for IO-bound jobs and `1 <= CPU_COUNT <= 61` for CPU-bound ones.

If you want to configure those max worker values, you can do so via the `MAX_THREAD_WORKERS` and `MAX_PROCESS_WORKERS` environment variables.

### Invoke a job normally if you want to run it immediately.

Invoking a job as a regular function allows you to run a job as if it were one. If you have logic that you only want to execute when enqueued, include a parameter with type `Context` and check if it exists at runtime (functions with a `Context` that are run immediately will have that argument set to `None`).

```python
@job()
async def context_aware(ctx: Context, msg: str):
    if ctx:
        # enqueued then run by arq
        return f"hello {msg}"
    else:
        # invoked manually
        return f"bye {msg}"

await context_aware("world") == "bye world"

j = await p.enqueue_job("context_aware", "world")
await j.result() == "hello world"
```

### Define WorkerSettings using the `BaseSettings` metaclass.

The execution logic that `@job` provides requires some stuff. When you defining your WorkerSettings, you must declare `BaseSettings` as its metaclass to ensure that stuff exists.

```python
class Settings(metaclass=BaseSettings):
    redis_settings = ...
```

### Use `Settings.create_pool()`.

While you may elect to use `arq.connections.create_pool` as you would normally, using the `create_pool` function provided by your `Settings` class ensures the pool it creates always matches your worker's Redis and serialization settings (it will be less of a headache). It also lets you take advantage of additional functionality, namely that it can be used as an auto-closing context manager.

```python
# manually
pool = await Settings.create_pool()
await pool.close(close_connection_pool=True)

# or as an async context manager
async with Settings.create_pool() as pool:
    ...
```

### Sign your job serializations with `blake2b`.

By default, using just-jobs `Settings` means all serialized jobs are prefixed with a signature which is then parsed and validated before job execution. This helps ensure that any jobs you serialize do not get tampered with while enqueued and waiting for execution. The default (and very insecure) secret used for signing is `thisisasecret`. In any production or public-facing deployment, you _should_ change this value to something private and secure. It can be changed via the `JOB_SERIALIZATION_SECRET` environment variable.

### Enqueue your job.

just-jobs doesn't change the way in which you enqueue your jobs. Just use `await pool.enqueue_job(...)`. Using just-jobs, you also don't have to worry as much about the type of arguments you supply; all Python objects supported by the [dill](http://dill.rtfd.io/) serialization library will work just fine.

```python
await pool.enqueue_job('complex_math', 2, 1, 3)
```

## Caveats

1. `arq.func()` and `@job()` are mutually exclusive. If you want to configure a job in the same way, pass the settings you would have passed to `func()` to `@job()` instead.

   ```python
   @job(job_type=JobType.CPU_BOUND, keep_result_forever=True, max_tries=10)
   def task(a: int, b: int):
      return a + b
   ```

2. There isn't support for asynchronous CPU-bound tasks. Currently, job types only configure the execution behavior of synchronous tasks (not coroutines). However, there are some valid cases for CPU-bound tasks that also need to be run in an asyncio context.

   At the moment, the best way to achieve this will be to create a synchronous CPU-bound task (so it runs in a separate process) that then invokes a coroutine via `asyncio.run`. If you intend on running the task in the current context from time to time, just return the coroutine instead and it will get automatically executed in the current event loop.

   ```python
   async _async_task(a: int, b: int, c: int):
       ab = await add(a, b)
       return await add(ab, c)

   @job(job_type=JobType.CPU_BOUND)
   def wrapper_cpu_bound(ctx: Context, a: int, b: int, c: int):
       task = _async_task(a, b, c)
       return asyncio.run(task) if ctx else task
   ```

## Example

The complete example is available at [docs/example.py](https://github.com/thearchitector/just-jobs/blob/main/docs/example.py) and should work out of the box. The snippet below is just an excerpt to show the features described above:

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
    url = sync_task("https://www.theglassfiles.com")

    await pool.enqueue_job("async_task", "https://www.eliasfgabriel.com")
    await pool.enqueue_job("sync_task", "https://gianturl.net")

    await pool.close(close_connection_pool=True)
```

## License

This software is licensed under the [3-Clause BSD License](LICENSE).

This package is [Treeware](https://treeware.earth). If you use it in production, consider [**buying the world a tree**](https://ecologi.com/eliasgabriel?r=6128126916bfab8bd051026c) to thank me for my work. By contributing to my forest, you’ll be creating employment for local families and restoring wildlife habitats.
