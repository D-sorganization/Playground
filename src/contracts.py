from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")


def require(
    condition: Callable[P, bool], message: str = "Precondition failed"
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            if not condition(*args, **kwargs):
                raise ValueError(message)
            return func(*args, **kwargs)

        return wrapper

    return decorator


def ensure(
    condition: Callable[[R], bool], message: str = "Postcondition failed"
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            result = func(*args, **kwargs)
            if not condition(result):
                raise RuntimeError(message)
            return result

        return wrapper

    return decorator
