import asyncio
import inspect
import warnings
from dataclasses import dataclass, field
from functools import partial, update_wrapper
from typing import Any, Awaitable, Callable, Generic, Optional, Union, cast

import dill  # type: ignore
from arq.typing import SecondsTimedelta, WorkerCoroutine
from arq.utils import to_seconds
from arq.worker import Function
from colorama import Fore, Style

from .job_type import JobType
from .typing import (
    ArqCallable,
    Context,
    ReturnType,
)
from .utils import convert_kwargs, styled_text


@dataclass
class _job(Function, Generic[ReturnType]):
    coroutine: WorkerCoroutine = field(init=False)

    func: ArqCallable[ReturnType]
    iscoro: bool = field(init=False, default=False)
    job_type: Optional[JobType] = None

    def __post_init__(self) -> None:
        if inspect.iscoroutinefunction(self.func):
            # async jobs always run in the thread of the event loop, even if
            # they're CPU-bound.
            if self.job_type:
                warnings.warn(
                    "Specifying a JobType on an asynchronous job does not affect how"
                    " it is executed.",
                    stacklevel=2,
                )

            self.iscoro = True
        elif not self.job_type:
            raise TypeError(
                "Synchronous jobs must be explicitly declared as either IO-bound"
                " or CPU-bound via a JobType."
            )

        self.coroutine = self.run
        update_wrapper(self, self.func)

    async def now(self, *args: Any, **kwargs: Any) -> ReturnType:
        warnings.warn(
            ".now() is deprecated, as the preferred way of immediately invoking a job"
            " is just as you would a normal function, ie. func().",
            DeprecationWarning,
            stacklevel=2,
        )
        result = self(*args, **kwargs)

        if inspect.iscoroutine(result):
            return await cast(Awaitable[ReturnType], result)

        return cast(ReturnType, result)

    def __call__(
        self, *args: Any, **kwargs: Any
    ) -> Union[ReturnType, Awaitable[ReturnType]]:
        """
        Runs the job immediately with a `context` argument set to None. If either
        the job or the result of the job is an asynchronous coroutine, it will
        be also be awaited.
        """
        nkwargs = convert_kwargs(None, self.func, args, kwargs)
        return self.func(**nkwargs)

    async def run(self, ctx: Context, *args: Any, **kwargs: Any) -> ReturnType:
        # we shouldn't / cannot pickle the redis instance nor underlying context
        # executors, so remove them from the context
        nctx = {k: ctx[k] for k in ctx if k not in ["redis", "_executors"]}
        nkwargs = convert_kwargs(nctx, self.func, args, kwargs)

        with styled_text(Fore.BLACK, Style.BRIGHT):
            if not self.iscoro:
                executor = ctx["_executors"][self.job_type]
                serialized = dill.dumps(partial(self.func, **nkwargs))
                return await asyncio.get_running_loop().run_in_executor(
                    executor, _job._dill_executor_func, serialized
                )
            else:
                return await cast(Awaitable[ReturnType], self.func(**nkwargs))

    @staticmethod
    def _dill_executor_func(serialized: bytes) -> ReturnType:
        # must be a separate function for process pool pickling
        partial: Callable[[], ReturnType] = dill.loads(serialized)
        return partial()


def job(
    job_type: Optional[JobType] = None,
    name: Optional[str] = None,
    keep_result: Optional[SecondsTimedelta] = None,
    timeout: Optional[SecondsTimedelta] = None,
    keep_result_forever: Optional[bool] = None,
    max_tries: Optional[int] = None,
) -> Callable[[ArqCallable[Any]], _job[Any]]:
    """
    Creates an async enqueueable job from the provided function. The function may be
    synchronous or a coroutine. If synchronous, the job will be run in either a
    thread or process depending on its `JobType`.

    Synchronous jobs are required to specify their `job_type`. If a job type is
    specified for a coroutine, a warning will be thrown (but will still execute).
    """
    return lambda func: _job(
        func=func,
        job_type=job_type,
        # inherited
        name=name or func.__qualname__,
        timeout_s=to_seconds(timeout),
        keep_result_s=to_seconds(keep_result),
        keep_result_forever=keep_result_forever,
        max_tries=max_tries,
    )
