"""
Module for providing a robust command-line interface (CLI) framework for managing
Machine Learning pipelines, specifically designed for Kubeflow Pipelines (KFP)
on Google Cloud's Vertex AI platform.

It defines custom argparse actions for flexible argument parsing and functions
to set up a generic argument parser and dispatch commands to a pipeline instance.

Key Features:
- Custom argparse actions for parsing key-value pairs and transforming strings.
- Generic argument parser setup for 'deploy', 'schedule', and 'submit' pipeline commands.
- Command dispatcher to execute pipeline methods based on parsed arguments.

This CLI is intended to be imported and used by ML wrapper repositories, allowing
them to expose a consistent command-line interface for their specific ML pipelines
without re-implementing argument parsing logic.
"""

from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from argparse import Namespace as argparseNamespace
from typing import Any

from loguru import logger

from .configs import SubmitSettings
from .utils.cli import ArgParseKeyValuePairs, ArgParseUnderscoreToSpace


def get_pipeline_commands_and_arguments(
    description: str, pipeline_name: str, pipeline_description: str, experiment_name: str
) -> ArgumentParser:
    """
    Configures and returns an ArgumentParser for generic ML pipeline commands.

    This function sets up a command-line interface with subcommands for
    'deploy', 'schedule', and 'submit' operations related to ML pipelines.
    It includes common arguments required for these operations, making it
    reusable across different pipeline projects.

    Parameters
    ----------
    description: str
        Help text to display before the argument help for the main parser.
    pipeline_name: str
        The name of the pipeline, used in help descriptions of subparsers.
        E.g., "MyMLPipeline".
    pipeline_description: str
        A brief description of the pipeline, used in the help output for subparsers.
    experiment_name: str
        The default experiment name for commands that take an optional
        `--experiment-name` parameter.

    Returns
    -------
    ArgumentParser
        An ArgumentParser object configured with pipeline management commands.

    Usage Example in an ML Wrapper Project:
    --------------------------------------
    ```python
    from ml_orchestrator.cli import get_pipeline_commands_and_arguments
    from ml_orchestrator.pipeline_assembly import GenericPipeline # Assuming your pipeline inherits this
    from ml_orchestrator.configs.abstractions import PipelineSettings # For pipeline settings

    # Define a dummy pipeline for demonstration
    class MyConcretePipeline(GenericPipeline):
        def __init__(self, settings: PipelineSettings):
            super().__init__(settings)
        def _create_pipeline_job(self):
            # Placeholder for actual KFP pipeline function
            pass
        def submit(self, experiment_name, only_validate, wait_for_completion, wipe_repo, branch):
            print(f"Submitting pipeline: {self.config.pipeline_display_name}")
            print(f"Experiment: {experiment_name}, Validate: {only_validate}, Wait: {wait_for_completion}")
            print(f"Branch: {branch}")
        def schedule(self, job_name, name, expression, display_name, description):
            print(f"Scheduling pipeline: {self.config.pipeline_display_name}")
            print(f"Job: {job_name}, Name: {name}, Cron: {expression}")

    if __name__ == "__main__":
        # Example pipeline settings
        settings = PipelineSettings(
            pipeline_display_name="MyTestPipeline",
            pipeline_root="gs://my-bucket/pipelines",
            experiment_name="default-experiment"
        )
        my_pipeline = MyConcretePipeline(settings)

        # Get the configured parser
        parser = get_pipeline_commands_and_arguments(
            description="CLI for managing MyTestPipeline",
            pipeline_name="MyTestPipeline",
            pipeline_description="Manages submission and scheduling of MyTestPipeline.",
            experiment_name=settings.experiment_name
        )

        # Parse command-line arguments
        args = parser.parse_args()

        # Dispatch the command to the pipeline instance
        run_pipeline_command(my_pipeline, args)
    ```
    Then run from terminal:
    `python your_main_script.py submit --experiment-name "my-exp" --branch repo1=feat/1`
    `python your_main_script.py schedule --name "daily-run" --expression "0_0_*_*_*" --job-name "job-id-123"
    """
    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter, description=description)

    # Global argument to register components
    parser.add_argument(
        "--register",
        action="store_true",
        help="Register all components."
        " If not used, only register components which have `componentname_default_register` set to True",
    )

    # Setup subparsers for different pipeline commands (submit, schedule, deploy)
    subparsers = parser.add_subparsers(
        title=f"{pipeline_name} Pipeline Commands",
        description=f"{pipeline_description}",
        dest="command",  # Stores the name of the subcommand that was invoked
        metavar="{{deploy,schedule,submit}}",  # Changes the displayed name for dest in help output
        required=True,  # Ensures one command is mandatory
        help="one command is mandatory",
    )

    # --- 'deploy' subcommand ---
    _parser_deploy = subparsers.add_parser(
        "deploy",
        formatter_class=ArgumentDefaultsHelpFormatter,
        help=f"Deploy '{pipeline_name}' pipeline to an endpoint.",
    )
    # Note: 'deploy' command currently raises NotImplementedError in run_pipeline_command.

    # --- 'schedule' subcommand ---
    parser_schedule = subparsers.add_parser(
        "schedule",
        formatter_class=ArgumentDefaultsHelpFormatter,
        help=(f"Update or create schedule for '{pipeline_name}' pipeline in '{experiment_name}' experiment."),
    )
    parser_schedule.add_argument(
        "--experiment-name",
        default=f"{experiment_name}",
        help="The name of the experiment to associate with the schedule.",
    )
    parser_schedule.add_argument(
        "--job-name",
        required=True,
        help="The existing pipeline job name (Run ID) to be scheduled. This acts as the template.",
    )
    parser_schedule.add_argument("--name", required=True, help="The unique name for the schedule.")
    parser_schedule.add_argument(
        "--expression",
        required=True,
        action=ArgParseUnderscoreToSpace,  # Uses custom action to convert underscores to spaces
        help=(
            "The cron expression of the schedule, following NCronTab format. Time zone CET is applied."
            " A crontab expression is composed of the space-delimited fields: 'MINUTES HOURS DAYS MONTHS DAYS-OF-WEEK'."
            " For example: '15 16 * * 1' means 4:15 PM CET every Monday."
            " Replacing underscores with spaces is supported to facilitate passing this string in shell scripts,"
            " for example: '15_16_*_*_1' is equivalent to passing '15 16 * * 1'."
        ),
    )
    parser_schedule.add_argument("--display-name", help="The display name of the schedule in the Vertex AI console.")
    parser_schedule.add_argument("--description", help="A description for the schedule.")

    # --- 'submit' subcommand ---
    parser_submit = subparsers.add_parser(
        "submit",
        formatter_class=ArgumentDefaultsHelpFormatter,
        help=(f"Submit '{pipeline_name}' pipeline in '{experiment_name}' experiment."),
    )
    parser_submit.add_argument(
        "--experiment-name",
        default=f"{experiment_name}",
        help="The name of the experiment to associate with the pipeline run.",
    )
    parser_submit.add_argument(
        "--only-validate",
        action="store_true",
        help="If set, the pipeline will be compiled but NOT submitted to Vertex AI. Useful for local validation.",
    )
    parser_submit.add_argument(
        "--wait-for-completion",
        action="store_true",
        help="If set, the CLI will block until the submitted pipeline run finishes.",
    )
    parser_submit.add_argument(
        "--wipe-repository-path",
        action="store_true",
        help=(
            "If set, any existing repository path will be wiped before cloning. "
            "Useful during pipeline development to ensure a clean state."
        ),
    )
    parser_submit.add_argument(
        "--branch",
        nargs="*",  # Allows zero or more arguments
        action=ArgParseKeyValuePairs,  # Uses custom action for key=value pairs
        type=str,
        help=(
            "Add key-value mappings of repository feature branches, "
            "e.g. '--branch eon-aml-image-classification=feature/1'. "
            "No spaces around the = sign is allowed. "
            "Only repositories relevant for the pipeline in question will be considered. "
            "Useful during development of the pipeline."
        ),
    )

    return parser


def run_pipeline_command(pipeline: Any, arguments: argparseNamespace) -> None:
    """
    Dispatches the parsed command-line arguments to the appropriate method
    of the provided pipeline instance.

    This function acts as a central router, taking the command identified
    by `get_pipeline_commands_and_arguments` and calling the corresponding
    method (`submit`, `schedule`, `deploy`) on the `pipeline` object.

    Parameters
    ----------
    pipeline: Any
        An instance of a pipeline class (expected to be a subclass of
        `GenericPipeline` from `ml_orchestrator.pipeline_assembly`).
        This object must have `submit`, `schedule`, and potentially `deploy` methods.
    arguments: argparseNamespace
        The namespace object returned by `ArgumentParser.parse_args()`,
        containing the parsed command-line arguments.

    Raises
    ------
    NotImplementedError
        If the 'deploy' command is invoked, as it's explicitly marked as not implemented.
    ValueError
        If an unknown command is encountered (should not happen if `required=True`
        is used in `add_subparsers`).
    AttributeError
        If the `pipeline` object does not have the method corresponding to the command.
        This indicates a mismatch between the CLI definition and the pipeline class's API.
    """
    try:
        # Dispatch based on the 'command' attribute set by subparsers
        if arguments.command == "submit":
            # Instantiate the settings dataclass from the parsed arguments
            settings = SubmitSettings(
                experiment_name=arguments.experiment_name,
                only_validate=arguments.only_validate,
                wait_for_completion=arguments.wait_for_completion,
                wipe_repository_path=arguments.wipe_repository_path,
                branch=arguments.branch,
            )
            pipeline.submit(settings)
        elif arguments.command == "schedule":
            # Call the schedule method of the pipeline instance with parsed arguments
            pipeline.schedule(
                arguments.job_name,
                arguments.name,
                arguments.expression,
                arguments.display_name,
                arguments.description,
            )
        elif arguments.command == "deploy":
            # 'deploy' command is explicitly not implemented yet
            raise NotImplementedError("Deployment is not yet implemented")
        else:
            # Fallback for unknown commands (should be caught by argparse if required=True)
            raise ValueError("Unknown command!")
    except AttributeError:
        # Catch if the pipeline object doesn't have the expected method
        logger.error("Unknown method/attribute on pipeline instance! Check pipeline implementation.")
        raise
