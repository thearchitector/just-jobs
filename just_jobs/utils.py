import inspect
from contextlib import contextmanager
from typing import Any, Callable, Dict, Generator, Optional, Tuple

from colorama import Style, just_fix_windows_console

from .typing import Context

just_fix_windows_console()


@contextmanager
def styled_text(*ansi_codes: str) -> Generator[None, None, None]:
    """
    Provides a context manager for temporarily printing styled text. The provided
    styles are applied and then reset when the block is exited.
    """
    try:
        print("".join(ansi_codes), end="", flush=True)
        yield
    finally:
        print(Style.RESET_ALL, end="", flush=True)


def convert_kwargs(
    ctx: Optional[Context],
    func: Callable[..., Any],
    args: Tuple[Any, ...],
    kwargs: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Given the function, convert the ordered arguments into kwargs based on the function
    signature. If the signature includes a Context parameter, inject it.

    TODO: maybe restrict Context to first or last param to reduce confusion?
    """
    iterargs = iter(args)

    injected = False
    for name, param in inspect.signature(func).parameters.items():
        if name not in kwargs:
            if param.annotation == Context:
                if injected:
                    raise AttributeError(
                        "Context should only be defined once in a job's signature."
                    )

                kwargs[name] = ctx
                injected = True
            else:
                kwargs[name] = next(iterargs)

    return kwargs
