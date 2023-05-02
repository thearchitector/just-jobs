from typing import Any, Awaitable, Callable, Dict, TypeVar, Union

Context = Dict[Any, Any]

ReturnType = TypeVar("ReturnType")  # anything
KwargsType = TypeVar("KwargsType")
ArgsType = TypeVar("ArgsType")
# define either a func or a coroutine func
ArqCallable = Callable[..., Union[ReturnType, Awaitable[ReturnType]]]
# a coroutine func
DecoratorCallable = Callable[..., Awaitable[ReturnType]]
