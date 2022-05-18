"""
Python package `just_jobs` provides a lightweight asynchronous Python job executor.
Using Redis by default (but not exclusivly, via custom Brokers), it is a smaller and
production-ready alternative to Celery for applications where distributed microservices
are overkill.

## What is a "job"?

A job is any exposed function, asynchronous coroutine, or generic callable that has
been queued to a worker for delayed execution by calling `Manager.enqueue`.

"Exposed" means the callable must be importable through a module-reference
FQN string, such as "just_jobs.Manager.enqueue". This is due to a limitation with Python
[pickling](https://docs.python.org/3/library/pickle.html).
"""

from .brokers import Broker, RedisBroker
from .manager import Manager

__all__ = ["Manager", "Broker", "RedisBroker"]
