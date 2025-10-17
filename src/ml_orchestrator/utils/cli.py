from argparse import Action, ArgumentDefaultsHelpFormatter, ArgumentError, ArgumentParser
from argparse import Namespace as ArgparseNamespace
from collections.abc import Sequence
from typing import Any

import kfp
from google.cloud import aiplatform
from ml_orchestrator import logger
from ml_orchestrator.pipelines import GenericPipeline

class ArgParseKeyValuePairs(Action):
    """Argparse action to split KEY=VALUE arguments into a dictionary."""

    def __call__(
        self,
        parser: ArgumentParser,
        namespace: ArgparseNamespace,
        values: str | Sequence[Any] | None,
        option_string: str | None = None,
    ) -> None:
        """
        Parse a single KEY=VALUE argument and append to a dictionary.

        Args:
            parser: The ArgumentParser containing this action.
            namespace: The Namespace object for parsed arguments.
            values: The command-line arguments, with type conversions applied.
            option_string: The option string invoking this action.

        Raises:
            ArgumentError: If the argument cannot be parsed as key=value pairs.
        """
        previous = getattr(namespace, self.dest, None) or dict()
        try:
            added = dict(map(lambda x: x.split("="), values))  # type: ignore[arg-type]
        except ValueError as exc:
            raise ArgumentError(
                self, f"Could not parse --{self.dest} with value '{values}' as k1=v1 k2=v2 format"
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
        """
        Parse a single argument, converting underscores to spaces.

        Args:
            parser: The ArgumentParser containing this action.
            namespace: The Namespace object for parsed arguments.
            values: The command-line arguments, with type conversions applied.
            option_string: The option string invoking this action.
        """
        if isinstance(values, str):
            setattr(namespace, self.dest, values.replace("_", " "))

def get_pipeline_commands_and_arguments(
    description: str, pipeline_name: str, pipeline_description: str, experiment_name: str
) -> ArgumentParser:
    """
    Set up command-line arguments for GCP Vertex AI/Kubeflow pipeline operations.

    Supports commands: submit, schedule, deploy.

    Args:
        description: Help text to display before argument help.
        pipeline_name: Pipeline name for help descriptions.
        pipeline_description: Pipeline description for sub-parser group.
        experiment_name: Default experiment name for commands.

    Returns:
        ArgumentParser: Parser for command-line arguments.
    """
    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter, description=description)

    parser.add_argument(
        "--register",
        action="store_true",
        help="Register all pipeline components. If not set, only register components with default_register=True."
    )
    parser.add_argument(
        "--project-id",
        default="my-gcp-project",
        help="GCP project ID for Vertex AI."
    )
    parser.add_argument(
        "--region",
        default="us-central1",
        help="GCP region for Vertex AI and Cloud Scheduler."
    )

    subparsers = parser.add_subparsers(
        title=f"{pipeline_name} Pipeline Commands",
        description=pipeline_description,
        dest="command",
        metavar="{deploy,schedule,submit}",
        required=True,
        help="One command is mandatory."
    )

    # Deploy command
    parser_deploy = subparsers.add_parser(
        "deploy",
        formatter_class=ArgumentDefaultsHelpFormatter,
        help=f"Deploy '{pipeline_name}' pipeline to a Vertex AI endpoint."
    )
    parser_deploy.add_argument(
        "--endpoint-name",
        required=True,
        help="Name of the Vertex AI endpoint to create or update."
    )

    # Schedule command
    parser_schedule = subparsers.add_parser(
        "schedule",
        formatter_class=ArgumentDefaultsHelpFormatter,
        help=f"Create or update schedule for '{pipeline_name}' pipeline in '{experiment_name}' experiment."
    )
    parser_schedule.add_argument(
        "--experiment-name",
        default=experiment_name,
        help="Name of the experiment."
    )
    parser_schedule.add_argument(
        "--job-name",
        required=True,
        help="Vertex AI pipeline job name or ID."
    )
    parser_schedule.add_argument(
        "--name",
        required=True,
        help="Name of the Cloud Scheduler job."
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
        )
    )
    parser_schedule.add_argument(
        "--display-name",
        help="Display name of the schedule."
    )
    parser_schedule.add_argument(
        "--description",
        help="Description of the schedule."
    )

    # Submit command
    parser_submit = subparsers.add_parser(
        "submit",
        formatter_class=ArgumentDefaultsHelpFormatter,
        help=f"Submit '{pipeline_name}' pipeline in '{experiment_name}' experiment."
    )
    parser_submit.add_argument(
        "--experiment-name",
        default=experiment_name,
        help="Name of the experiment."
    )
    parser_submit.add_argument(
        "--only-validate",
        action="store_true",
        help="Validate pipeline without submitting. Useful for development."
    )
    parser_submit.add_argument(
        "--wait-for-completion",
        action="store_true",
        help="Wait for pipeline completion."
    )
    parser_submit.add_argument(
        "--wipe-repository-path",
        action="store_true",
        help="Wipe existing repository path before cloning. Useful for development."
    )
    parser_submit.add_argument(
        "--branch",
        nargs="*",
        action=ArgParseKeyValuePairs,
        type=str,
        help=(
            "Key-value mappings of repository feature branches, "
            "e.g., '--branch my-repo=feature/1'. No spaces around '=' allowed."
        )
    )

    return parser

def run_pipeline_command(pipeline: GenericPipeline, arguments: ArgparseNamespace) -> None:
    """
    Run the specified pipeline command using the provided arguments.

    Args:
        pipeline: The GenericPipeline instance to execute.
        arguments: Parsed command-line arguments.

    Raises:
        ValueError: If an unknown command is specified.
        AttributeError: If a required method or attribute is missing.
        Exception: For deployment or other operation failures.
    """
    try:
        if arguments.command == "submit":
            logger.info(f"Executing submit command for pipeline in experiment {arguments.experiment_name}")
            pipeline.submit(
                experiment_name=arguments.experiment_name,
                only_validate=arguments.only_validate,
                wait_for_completion=arguments.wait_for_completion,
                wipe_repository_path=arguments.wipe_repository_path,
                branch=arguments.branch or {},
            )
        elif arguments.command == "schedule":
            logger.info(f"Executing schedule command for job {arguments.job_name}")
            pipeline.schedule(
                job_name=arguments.job_name,
                name=arguments.name,
                expression=arguments.expression,
                display_name=arguments.display_name,
                description=arguments.description,
            )
        elif arguments.command == "deploy":
            logger.info(f"Deploying pipeline to endpoint {arguments.endpoint_name}")
            # Basic deployment to Vertex AI endpoint
            pipeline_job = pipeline._create_pipeline_job()
            pipeline_spec_path = f"/tmp/{pipeline_job.__name__}.yaml"
            kfp.compiler.Compiler().compile(pipeline_job, pipeline_spec_path)
            job = aiplatform.PipelineJob(
                display_name=pipeline_job.__name__,
                template_path=pipeline_spec_path,
                pipeline_root=f"gs://{pipeline.gcs_bucket}/pipelines",  # Use pipeline's GCS bucket
                project=arguments.project_id,
                location=arguments.region,
                labels={"experiment": arguments.experiment_name},
                service_account=pipeline.service_account,
            )
            job.run()  # Run pipeline to generate model
            model = aiplatform.Model(model_name=f"{pipeline_job.__name__}-model")  # Assumes model output
            endpoint = aiplatform.Endpoint.create(display_name=arguments.endpoint_name)
            endpoint.deploy(model)
            logger.info(f"Deployed pipeline to endpoint {endpoint.resource_name}")
        else:
            raise ValueError(f"Unknown command: {arguments.command}")
    except AttributeError as e:
        logger.error(f"Unknown method/attribute: {e}")
        raise
    except Exception as e:
        logger.error(f"Pipeline command failed: {e}")
        raise