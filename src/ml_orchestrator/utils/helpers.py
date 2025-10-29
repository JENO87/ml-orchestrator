import functools
import os
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, cast

import tomllib
from loguru import logger


@lru_cache(maxsize=1)
def _load_pyproject() -> dict[str, Any]:
    """Load pyproject.toml from the repository root – works everywhere."""
    # CI can force the path (optional safety net)
    if override := os.getenv("PYPROJECT_TOML_PATH"):
        path = Path(override)
        if not path.is_file():
            raise FileNotFoundError(f"PYPROJECT_TOML_PATH not found: {path}")
        with path.open("rb") as f:
            return tomllib.load(f)

    # Walk up from this file
    cur = Path(__file__).resolve()
    for _ in range(10):
        candidate = cur / "pyproject.toml"
        if candidate.is_file():
            with candidate.open("rb") as f:
                return tomllib.load(f)
        if cur == cur.parent:
            break
        cur = cur.parent
    raise FileNotFoundError("pyproject.toml not found")


def get_optional_deps(component_name: str) -> list[str]:
    """Return the list from [project.optional-dependencies.<component_name>]."""
    data = _load_pyproject()
    deps = data.get("project", {}).get("optional-dependencies", {}).get(component_name.lower(), [])
    return cast(list[str], deps)


def create_docker_image(specs: Any) -> str:
    from ml_orchestrator.configs.abstractions import VarTemplateComponent  # pylint: disable=import-outside-toplevel

    assert isinstance(specs, VarTemplateComponent), "specs must be an instance of VarTemplateComponent"
    # --- Dockerfile Generation ---
    dockerfile = f"""FROM {specs.base_image}
    WORKDIR /app
    """

    # Add dependency installation from pyproject.toml
    component_deps = specs._get_component_deps()
    if component_deps:
        project = specs._get_project_name()
        deps = " ".join(component_deps)
        dockerfile += f'RUN pip install --no-cache-dir "{project}[{deps}]"\n'

    # Add command to get the component code into the image
    if specs.source_repo_url:
        # Source is a remote git repo, so we curl the file
        dockerfile += (
            f"RUN mkdir -p $(dirname {specs.target_path}) && curl -L {specs.full_script_url} -o {specs.target_path}\n"
        )
    elif specs.source_package_spec:
        # Source is a Python package, so we pip install it
        dockerfile += f'RUN pip install "{specs.source_package_spec}"\n'

    # --- Build and Push ---
    filename = f"Dockerfile.{specs.component_name}"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(dockerfile)

    tag = specs.image_tag()
    try:
        subprocess.run(["docker", "build", "-f", filename, "-t", tag, "."], check=True)
        subprocess.run(["docker", "push", tag], check=True)
    finally:
        # Clean up the temporary Dockerfile
        os.remove(filename)

    return tag


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


def build_cron_expression(
    minute: str = "*",
    hour: str = "*",
    day_of_month: str = "*",
    month: str = "*",
    day_of_week: str = "*",
) -> str:
    """Builds a cron expression string from individual time components.

    Each component can be a specific value (e.g., '0', '15'), a list of values
    (e.g., '0,30'), a range (e.g., '9-17'), a step (e.g., '*/5'), or '*' for all.
    All values are interpreted in UTC.

    Args:
        minute: Minute (0-59 or '*').
        hour: Hour (0-23 or '*').
        day_of_month: Day of month (1-31 or '*').
        month: Month (1-12 or '*' or JAN-DEC).
        day_of_week: Day of week (0-6 or '*' or SUN-SAT, 0 and 7 are Sunday).

    Returns
    -------
        A cron expression string.

    Examples
    --------
        >>> build_cron_expression(minute="30", hour="3")
        '30 3 * * *'  # Daily at 3:30 AM UTC
        >>> build_cron_expression(minute="0", hour="9", day_of_week="1")
        '0 9 * * 1'   # Every Monday at 9:00 AM UTC
        >>> build_cron_expression(minute="*/15")
        '*/15 * * * *' # Every 15 minutes
    """
    return f"{minute} {hour} {day_of_month} {month} {day_of_week}"
