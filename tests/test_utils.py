import pytest
from colorama import Fore, Style

from just_jobs import Context
from just_jobs.utils import convert_kwargs, styled_text


def test_styled_text(pcapture):
    with pcapture as target:
        with styled_text(Fore.GREEN):
            print("this should be green")

    assert target.getvalue() == Fore.GREEN + "this should be green\n" + Style.RESET_ALL


def f0(x: int, y: int, z: int = 0):
    return x == 0 and y == 1 and z == 2


def f1(x: int, y: int):
    return x == 0 and y == 1


def f2(z: int = 0):
    return z == 2


def f3(x: int, z: int = 0, *, y: int):
    return x == 0 and y == 1 and z == 2


def f4(ctx: Context, x: int, y: int, z: int = 0):
    return ctx == {} and x == 0 and y == 1 and z == 2


def f5(x: int, ctx: Context, y: int, z: int = 0):
    return ctx == {} and x == 0 and y == 1 and z == 2


@pytest.mark.parametrize(
    "func,args,kwargs,expected",
    [
        (f0, (0, 1), {"z": 2}, {"x": 0, "y": 1, "z": 2}),
        (f1, (0, 1), {}, {"x": 0, "y": 1}),
        (f2, (), {"z": 2}, {"z": 2}),
        (f3, (0, 1), {"z": 2}, {"x": 0, "y": 1, "z": 2}),
        (f4, (0, 1), {"z": 2}, {"x": 0, "y": 1, "z": 2, "ctx": {}}),
        (f5, (0, 1), {"z": 2}, {"x": 0, "y": 1, "z": 2, "ctx": {}}),
    ],
    ids=[
        "ordered",
        "args-only",
        "kwargs-only",
        "jumbled",
        "ordered-context",
        "jumbled-context",
    ],
)
def test_convert_kwargs(func, args, kwargs, expected):
    assert convert_kwargs({}, func, args, kwargs) == expected
    assert func(**expected)


def test_convert_kwargs_multictx():
    def f6(ctx: Context, x: int, y: int, ctx2: Context, z: int = 0):
        pass

    with pytest.raises(AttributeError, match="Context should only"):
        convert_kwargs({}, f6, (0, 1), {"z": 2})
