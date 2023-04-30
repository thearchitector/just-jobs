from contextlib import contextmanager

from colorama import Style, just_fix_windows_console

just_fix_windows_console()


@contextmanager
def styled_text(*ansi_codes: str):
    """
    Provides a context manager for temporarily printing styled text. The provided
    styles are applied and then reset when the block is exited.
    """
    try:
        print("".join(ansi_codes), end="", flush=True)
        yield
    finally:
        print(Style.RESET_ALL, end="", flush=True)
