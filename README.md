# just-jobs

A lightweight asynchronous Python job executor backed by Redis.

## Usage

The entire execution structure consists of 3 things:

- The `Manager`, which is responsible for managing the broker and all job queues.
- The `Broker`, which is responsible for integrating into a storage interface and executing jobs.
- A `job`, which is any non-dynamic function or coroutine that performs some task.

In general, the process for enqueue jobs for execution is always the same:

1. Create a Manager and tell it to start listening for jobs via `await manager.startup()`.
2. Anywhere in your application, enqueue a job via `manager.enqueue(job, *args, **kwargs)`.
3. Ensure to properly shutdown your manager with `await manager.shutdown()`.

### Example

A common use case for delayed jobs is a web application, where milliseconds are important. Here is an example using FastAPI, whose startup and shutdown hooks make it easier for us to manage the state of our Manager.

```py
from fastapi import FastAPI
from just_jobs import Manager

app = FastAPI()

async def _essential_task(a, b):
    """render a movie, or email a user, or both"""

@app.on_event("startup")
async def startup():
    # the default broker is backed by Redis via aioredis. Managers
    # will always pass any args and kwargs it doesn't recognize to
    # their brokers during startup.
    manager = Manager(url="redis://important-redis-server/0")
    app.state.manager = manager
    await manager.startup()

@app.on_event("shutdown")
async def shutdown():
    # this is absolutely essential to allow the manager to shutdown
    # all the listening workers, as well as for the broker to do any
    # cleanup or disconnects it should from its backing storage inferface.
    await app.state.manager.shutdown()

@app.get("/do_thing")
async def root():
    # enqueue the task so it gets run in a worker's process queue
    await app.state.manager.enqueue(_essential_task, 2, 2)
    return {"message": "The thing is being done!"}
```
