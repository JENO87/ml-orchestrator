from argparse import (
    Action,
    ArgumentDefaultsHelpFormatter,
    ArgumentError,
    ArgumentParser,
    Namespace as ArgparseNamespace,
)
from collections.abc import Sequence
from typing import Any

from loguru import logger

from ml_orchestrator.configs import PipelineConfig
from ml_orchestrator.pipeline_assembly import GenericPipeline


class ArgParseKeyValuePairs(Action):
    """Argparse action to split KEY=VALUE arguments into a dictionary."""

    def __call__(
        self,
        parser: ArgumentParser,
        namespace: ArgparseNamespace,
        values: str | Sequence[Any] | None,
        option_string: str | None = None,
    ) -> None:
        """Parse a single KEY=VALUE argument and append to a dictionary.

        Args:
            parser: The ArgumentParser containing this action.
            namespace: The Namespace object for parsed arguments.
            values: The command-line arguments, with type conversions applied.
            option_string: The option string invoking this action.
        """
        previous = getattr(namespace, self.dest, None) or {}
        try:
            added = dict(map(lambda x: x.split("="), values))  # type: ignore[arg-type]
        except ValueError as exc:
            raise ArgumentError(
                self,
                f"Could not parse --{self.dest} with value '{{values}}' as "
                f"k1=v1 k2=v2 format",
            ) from exc
        merged = {**previous, **added}
        setattr(namespace, self.dest, merged)


class ArgParseUnderscoreToSpace(Action):
    """Argparse action to convert underscores to spaces in cron expressions."""

    def __call__(
        self,
        parser: ArgumentParser,
        namespace: ArgparseNamespace,
        values: str | Sequence[Any] | None,
        option_string: str | None = None,
    ) -> None:
        """Parse a single argument, converting underscores to spaces.

        Args:
            parser: The ArgumentParser containing this action.
            namespace: The Namespace object for parsed arguments.
            values: The command-line arguments, with type conversions applied.
            option_string: The option string invoking this action.
        """
        if isinstance(values, str):
            setattr(namespace, self.dest, values.replace("_", " "))


def get_pipeline_commands_and_arguments(
    description: str, pipeline_config: PipelineConfig
) -> ArgumentParser:
    """Set up command-line arguments for GCP Vertex AI/Kubeflow pipeline operations.

    Supports commands: submit, schedule.

    Args:
        description: Help text to display before argument help.
        pipeline_config: The PipelineConfig object containing pipeline metadata.

    Returns
    -------
        ArgumentParser: Parser for command-line arguments.
    """
    parser = ArgumentParser(
        formatter_class=ArgumentDefaultsHelpFormatter, description=description
    )

    subparsers = parser.add_subparsers(
        title=f"{pipeline_config.pipeline_display_name} Pipeline Commands",
        description=pipeline_config.pipeline_description,
        dest="command",
        metavar="{schedule,submit}",
        required=True,
        help="One command is mandatory.",
    )

    # Schedule command
    parser_schedule = subparsers.add_parser(
        "schedule",
        formatter_class=ArgumentDefaultsHelpFormatter,
        help=(
            f"Create or update schedule for "
            f"'{pipeline_config.pipeline_display_name}' pipeline."
        ),
    )
    parser_schedule.add_argument(
        "--expression",
        required=True,
        action=ArgParseUnderscoreToSpace,
        help=(
            "Cron expression for the schedule (NCronTab format, CET timezone). "
            "Format: 'MINUTES HOURS DAYS MONTHS DAYS-OF-WEEK'. "
            "Example: '15 16 * * 1' for 4:15 PM CET every Monday. "
            "Use underscores (e.g., '15_16_*_*_1') for shell compatibility."
        ),
    )

    # Submit command
    parser_submit = subparsers.add_parser(
        "submit",
        formatter_class=ArgumentDefaultsHelpFormatter,
        help=f"Submit '{pipeline_config.pipeline_display_name}' pipeline.",
    )
    parser_submit.add_argument(
        "--only-validate",
        action="store_true",
        help="Compile pipeline but do not submit.",
    )
    parser_submit.add_argument(
        "--wait-for-completion",
        action="store_true",
        help="Wait for pipeline completion.",
    )

    return parser


def run_pipeline_command(
    pipeline: GenericPipeline, arguments: ArgparseNamespace
) -> None:
    """Run the specified pipeline command using the provided arguments.

    Args:
        pipeline: The GenericPipeline instance to execute.
        arguments: Parsed command-line arguments.

    Raises
    ------
        ValueError: If an unknown command is specified.
        AttributeError: If a required method or attribute is missing.
        Exception: For deployment or other operation failures.
    """
    try:
        if arguments.command == "submit":
            logger.info(
                f"Executing submit command for pipeline "
                f"'{pipeline.config.pipeline_display_name}'"
            )
            pipeline.submit(
                only_validate=arguments.only_validate,
                wait_for_completion=arguments.wait_for_completion,
            )
        elif arguments.command == "schedule":
            logger.info(
                f"Executing schedule command for pipeline "
                f"'{pipeline.config.pipeline_display_name}'"
            )
            pipeline.schedule(
                cron_expression=arguments.expression,
            )
        else:
            raise ValueError(f"Unknown command: {arguments.command}")
    except AttributeError as e:
        logger.error(f"Unknown method/attribute: {e}")
        raise
    except Exception as e:
        logger.error(f"Pipeline command failed: {e}")
        raise
