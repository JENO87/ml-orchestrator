import functools
from typing import Any, Callable

from loguru import logger


def log_activity(func: Callable[..., Any]) -> Callable[..., Any]:
    """A decorator to log function calls, their arguments, and their execution.

    This helps in tracing the activity of key functions.
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        """Wrapper that adds logging before and after the function call."""
        logger.info(f"Executing: {func.__name__}")

        # To avoid excessive verbosity, we can choose what to log.
        # For instance, logging only the type of objects passed.
        arg_types = [type(a).__name__ for a in args]
        kwarg_types = {k: type(v).__name__ for k, v in kwargs.items()}
        logger.debug(f"With args (types): {arg_types}, kwargs (types): {kwarg_types}")

        result = func(*args, **kwargs)

        logger.info(f"Finished executing: {func.__name__}")
        return result

    return wrapper
