from typing import Any, Awaitable, Callable, Dict, TypeVar, Union

Context = Dict[Any, Any]
"""A type for defining the arq context dictionary passed to enqueue functions."""

ReturnType = TypeVar("ReturnType")
ArqCallable = Callable[
    ..., Union[ReturnType, Awaitable[ReturnType]]
]  # either a func or a coroutine func
