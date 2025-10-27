import functools
import os
import subprocess
from typing import Any, Callable

from loguru import logger

from ml_orchestrator.configs.abstractions import ComponentSpec


def create_docker_image(component_spec: ComponentSpec, registry: str) -> str:
    """Generate Dockerfile and build/push Docker image based on component spec."""
    script_url, target_paths, command = component_spec.get_build_config()
    dockerfile_content = f"""FROM {component_spec.base_image}
    WORKDIR /app
    """
    # Install component-specific dependencies
    if component_spec.packages_to_install:
        dockerfile_content += (
            f"RUN pip install --no-cache-dir ml-wrapper[{' '.join(component_spec.packages_to_install)}]\n"
        )
    # Add RUN commands for each target path
    for target_path in target_paths:
        dockerfile_content += f"RUN mkdir -p /scripts && curl -L {script_url} -o {target_path}\n"
    # Construct CMD with command and target path
    cmd_args = [command]
    if target_paths:
        cmd_args.append(target_paths[0])
    dockerfile_content += f"CMD {str(cmd_args)}\n"
    with open(f"{component_spec.component_name}.Dockerfile", "w", encoding="utf-8") as f:
        f.write(dockerfile_content)
    # Get environment from branch (e.g., 'development' from 'feature/development')
    env = os.environ.get("BRANCH_NAME", "development").split("/")[-1].lower()  # Default to 'development'
    # Get version from pyproject.toml via hatch or CI environment variable
    version = os.environ.get("VERSION", "0.1.0")  # Default to 0.1.0 if not set
    # Construct image tag: repo_name-component-environment:version
    if component_spec.component_name == "base":  # For base image
        image_tag = f"{registry}/ml-wrapper-{env}:{version}"
    else:  # For component images
        image_tag = f"{registry}/ml-wrapper-{component_spec.component_name}-{env}:{version}"
    subprocess.run(
        ["docker", "build", "-f", f"Dockerfile.{component_spec.component_name}", "-t", image_tag, "."], check=True
    )
    subprocess.run(["docker", "push", image_tag], check=True)
    return image_tag


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
