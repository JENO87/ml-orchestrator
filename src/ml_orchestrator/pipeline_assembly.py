import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional

from google.cloud import aiplatform
from google.cloud.aiplatform import PipelineJobSchedule
from kfp import compiler
from kfp.dsl.base_component import BaseComponent
from loguru import logger

from ml_orchestrator.configs.abstractions import PipelineSettings, SubmitSettings
from ml_orchestrator.project import GCPProject


class GenericPipeline(ABC, GCPProject):
    """Abstract base class for Kubeflow Pipelines on GCP Vertex AI.

    This class serves as a foundational wrapper, providing reusable logic for
    compiling, submitting, and scheduling Kubeflow Pipelines (KFP) to Google Cloud's
    Vertex AI platform. It is designed to be inherited by specific pipeline
    implementations in a 'wrapper' repository, allowing for consistent interaction
    with Vertex AI while keeping pipeline definitions separate and modular.

    Child classes must implement the `_create_pipeline_job` abstract method
    to define their specific KFP pipeline function.
    """

    def __init__(self, settings: PipelineSettings):
        """Initialize the GenericPipeline with GCP workspace and a configuration object.

        This constructor sets up the necessary GCP client connections (inherited from
        GCPProject) and stores the pipeline-specific configuration.

        Args:
            settings: A concrete implementation of PipelineSettings containing
                    pipeline-specific configuration like display names, GCS roots,
                    and experiment names. This configuration guides how the pipeline
                    is submitted and scheduled.
        """
        super().__init__()  # Initialize GCPProject, setting up Vertex AI, Storage,
        # Secret Manager clients
        self.config = settings
        self.vertex_client = aiplatform  # Expose the aiplatform client for direct use if needed

    @abstractmethod
    def _create_pipeline_job(self, **kwargs: Any) -> BaseComponent:
        """Abstract method that must be implemented by any child class.

        This method is responsible for defining and returning the actual Kubeflow
        Pipeline function. This function should be decorated with `@kfp.dsl.pipeline`
        and contain the graph of components that make up the pipeline.

        The leading underscore (`_`) indicates that this method is intended for
        internal use by the `GenericPipeline` class and its subclasses. It's not
        meant to be called directly by external code, promoting encapsulation.

        Args:
            **kwargs: Forwards arguments from the CLI, such as `branch` or `wipe_repo`,
                      to the concrete pipeline implementation.

        Example implementation in a child class:
        ```python
        from kfp import dsl
        from kfp.dsl import component

        @component
        def my_component_op(message: str):
            print(f"Hello from component: {message}")

        @dsl.pipeline(
            name="my-example-pipeline",
            description="A simple example KFP pipeline."
        )
        def my_kfp_pipeline(pipeline_message: str = "Default message"):
            my_component_op(message=pipeline_message)

        class MyConcretePipeline(GenericPipeline):
            def __init__(self, config: PipelineSettings):
                super().__init__(config)

            def _create_pipeline_job(self, **kwargs) -> BaseComponent:
                # kwargs might contain {'branch': {'my-repo': 'feature-branch'}}
                print(f"Arguments from CLI: {kwargs}")
                return my_kfp_pipeline
        ```

        Returns
        -------
            A callable KFP pipeline function (which is a BaseComponent instance
            after compilation).
        """
        raise NotImplementedError("Child class must implement _create_pipeline_job method.")

    def submit(self, settings: SubmitSettings) -> None:
        """Compiles the KFP pipeline and optionally submits it to Vertex AI
        for execution.

        This method orchestrates the process of taking a Python-defined KFP pipeline,
        compiling it into a YAML specification, and then using the Vertex AI SDK
        to create and run a PipelineJob.

        Args:
            settings: A dataclass containing all settings for the submission,
                      such as experiment name, validation options, and branches.
        """
        logger.info("Setting up Kubeflow pipeline job for submission.")

        # 1. Get the KFP pipeline function from the child class implementation
        pipeline_func = self._create_pipeline_job(branch=settings.branch, wipe_repo=settings.wipe_repository_path)

        # 2. Compile the KFP pipeline function into a YAML specification
        temp_dir = Path(tempfile.gettempdir())
        pipeline_spec_path = str(temp_dir / f"{self.config.pipeline_display_name}.yaml")
        compiler.Compiler().compile(pipeline_func, pipeline_spec_path)
        logger.info(f"Pipeline compiled to: {pipeline_spec_path}")

        if not settings.only_validate:
            logger.info(f"Submitting pipeline '{self.config.pipeline_display_name}' to Vertex AI.")

            # 3. Create a Vertex AI PipelineJob instance
            job = aiplatform.PipelineJob(
                display_name=self.config.pipeline_display_name,
                template_path=pipeline_spec_path,
                pipeline_root=self.config.pipeline_root,
                parameter_values=self.config.parameter_values,
                input_artifacts=self.config.input_artifacts,
                enable_caching=self.config.enable_caching,
                encryption_spec_key_name=self.config.encryption_spec_key_name,
                labels={**{"experiment": settings.experiment_name}, **self.config.labels},
                project=self.env.gcp.project_id,
                location=self.env.gcp.location,
                failure_policy=self.config.failure_policy,
            )

            # 4. Submit the PipelineJob to Vertex AI
            job.submit()
            logger.info(f"Submitted pipeline job: {job.resource_name}")
            logger.info(
                f"View job in console: https://console.cloud.google.com/vertex-ai/locations/"
                f"{self.env.gcp.location}/pipelines/runs/{job.name}?project={self.env.gcp.project_id}"
            )

            if settings.wait_for_completion:
                logger.info("Waiting for pipeline completion...")
                job.wait()
                logger.info(f"Pipeline '{job.display_name}' completed with state: {job.state}")
        else:
            logger.info("Validation completed, not submitting pipeline.")

    def schedule(
        self,
        name: str,
        expression: str,
        display_name: Optional[str],
    ) -> None:
        """Schedules the pipeline using GCP Vertex AI Pipeline Schedules.

        This method allows you to set up recurring executions of your pipeline
        based on a cron expression.

        Args:
            name: The unique name for the schedule.
            expression: A cron expression string for the schedule.
            display_name: The display name of the schedule in the Vertex AI console.
        """
        logger.info(f"Setting up pipeline schedule '{name}'.")

        # 1. Get the KFP pipeline function from the child class implementation
        pipeline_func = self._create_pipeline_job()

        # 2. Compile the KFP pipeline function into a YAML specification
        temp_dir = Path(tempfile.gettempdir())
        pipeline_spec_path = str(temp_dir / f"{self.config.pipeline_display_name}.yaml")
        compiler.Compiler().compile(pipeline_func, pipeline_spec_path)
        logger.info(f"Pipeline compiled to: {pipeline_spec_path}")

        # 3. Create a Vertex AI PipelineJob instance (this defines the job that will be scheduled)
        pipeline_job_instance = aiplatform.PipelineJob(
            display_name=self.config.pipeline_display_name,
            template_path=pipeline_spec_path,
            pipeline_root=self.config.pipeline_root,
            project=self.env.gcp.project_id,
            location=self.env.gcp.location,
            labels={**{"experiment": self.config.experiment_name}, **self.config.labels},
            enable_caching=self.config.enable_caching,
            parameter_values=self.config.parameter_values,
            failure_policy=self.config.failure_policy,
            input_artifacts=self.config.input_artifacts,
            encryption_spec_key_name=self.config.encryption_spec_key_name,
        )

        # 4. Create a PipelineJobSchedule instance
        schedule_display_name = display_name or f"{self.config.pipeline_display_name}-schedule"
        pipeline_job_schedule_instance = PipelineJobSchedule(
            pipeline_job=pipeline_job_instance,
            display_name=schedule_display_name,
        )

        # 5. Call create() on the PipelineJobSchedule instance to activate the schedule
        pipeline_job_schedule_instance.create(
            cron=expression,
            # Optional: max_concurrent_run_count, max_run_count, start_time, end_time
        )
        logger.info(f"Created schedule: {pipeline_job_schedule_instance.name}")
        logger.info(
            f"View schedule in console: https://console.cloud.google.com/vertex-ai/locations/"
            f"{self.env.gcp.location}/pipeline-job-schedules/{pipeline_job_schedule_instance.name}"
            f"?project={self.env.gcp.project_id}"
        )
