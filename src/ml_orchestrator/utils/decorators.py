import functools
import logging
from typing import Any, Callable

# Configure basic logging to display INFO level messages
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def log_activity(func: Callable[..., Any]) -> Callable[..., Any]:
    """A decorator to log function calls, their arguments, and their execution.

    This helps in tracing the activity of key functions.
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        """Wrapper that adds logging before and after the function call."""
        logging.info(f"Executing: {func.__name__}")

        # To avoid excessive verbosity, we can choose what to log.
        # For instance, logging only the type of objects passed.
        arg_types = [type(a).__name__ for a in args]
        kwarg_types = {k: type(v).__name__ for k, v in kwargs.items()}
        logging.debug(f"With args (types): {arg_types}, kwargs (types): {kwarg_types}")

        result = func(*args, **kwargs)

        logging.info(f"Finished executing: {func.__name__}")
        return result

    return wrapper
