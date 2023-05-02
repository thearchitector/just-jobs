import asyncio
import inspect
import warnings
from functools import partial, wraps
from typing import Any, Awaitable, Callable, Optional, cast

import dill  # type: ignore
from colorama import Fore, Style

from .job_type import JobType
from .typing import (
    ArgsType,
    ArqCallable,
    Context,
    DecoratorCallable,
    KwargsType,
    ReturnType,
)
from .utils import styled_text


# TODO: should be a class?
def job(
    job_type: Optional[JobType] = None,
) -> Callable[[ArqCallable[ReturnType]], DecoratorCallable[ReturnType]]:
    """
    Creates an async enqueueable job from the provided function. The function may be
    synchronous or a coroutine. If synchronous, the job will be run in either a thread
    or process depending on its `JobType`.

    Synchronous jobs are required to specify their `job_type`. If a job type is
    specified for a coroutine, a warning will be thrown (but will still execute).
    """

    def decorator(func: ArqCallable[ReturnType]) -> DecoratorCallable[ReturnType]:
        iscoro = inspect.iscoroutinefunction(func)
        if iscoro:
            # async jobs always run in the thread of the event loop, even if
            # they're CPU-bound.
            if job_type:
                warnings.warn(
                    "Specifying a JobType on an asynchronous job does not affect how"
                    " it is executed.",
                    stacklevel=2,
                )
        elif not job_type:
            raise TypeError(
                "Synchronous jobs must be explicitly declared as either IO-bound"
                " or CPU-bound via a JobType."
            )

        async def now(*args: ArgsType, **kwargs: KwargsType) -> ReturnType:
            """
            Runs the job immediately with a `context` argument set to None. If either
            the job or the result of the job is an asynchronous coroutine, it will
            be also be awaited.
            """
            result = func(None, *args, **kwargs)
            if inspect.iscoroutine(result):
                return await cast(Awaitable[ReturnType], result)
            return cast(ReturnType, result)

        setattr(func, "now", now)

        @wraps(func)
        async def wrapper(
            ctx: Context, *args: ArgsType, **kwargs: KwargsType
        ) -> ReturnType:
            # we shouldn't / cannot pickle the redis instance nor underlying context
            # executors, so remove them from the context. this is mainly a problem
            # for CPU-bound tasks running in a process pool, but do it for both for
            # consistency
            nctx: Context = {k: ctx[k] for k in ctx if k not in ["redis", "_executors"]}

            with styled_text(Fore.BLACK, Style.BRIGHT):
                if not iscoro:
                    executor = ctx["_executors"][job_type]
                    serialized = dill.dumps(partial(func, nctx, *args, **kwargs))
                    return await asyncio.get_running_loop().run_in_executor(
                        executor, _dill_executor_func, serialized
                    )
                else:
                    return await cast(
                        Awaitable[ReturnType], func(nctx, *args, **kwargs)
                    )

        return wrapper

    return decorator


def _dill_executor_func(serialized: bytes) -> Any:
    partial: Callable[[], Any] = dill.loads(serialized)
    return partial()
