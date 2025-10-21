from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from google.cloud import aiplatform
from kfp import compiler, dsl
from google.cloud.aiplatform import PipelineJobSchedule
from google.cloud.aiplatform.pipeline_jobs import PipelineJob
from kfp.dsl.base_component import BaseComponent
from loguru import logger

from ml_orchestrator.configs.abstractions import PipelineConfig
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

    def __init__(self, config: PipelineConfig):
        """Initialize the GenericPipeline with GCP workspace and a configuration object.

        This constructor sets up the necessary GCP client connections (inherited from
        GCPProject) and stores the pipeline-specific configuration.

        Args:
            config: A concrete implementation of PipelineConfig containing
                    pipeline-specific configuration like display names, GCS roots,
                    and experiment names. This configuration guides how the pipeline
                    is submitted and scheduled.
        """
        super().__init__()  # Initialize GCPProject, setting up Vertex AI, Storage, Secret Manager clients
        self.config = config
        self.vertex_client = aiplatform  # Expose the aiplatform client for direct use if needed

    @abstractmethod
    def _create_pipeline_job(self) -> BaseComponent:
        """Abstract method that must be implemented by any child class.

        This method is responsible for defining and returning the actual Kubeflow
        Pipeline function. This function should be decorated with `@kfp.dsl.pipeline`
        and contain the graph of components that make up the pipeline.

        The leading underscore (`_`) indicates that this method is intended for
        internal use by the `GenericPipeline` class and its subclasses. It's not
        meant to be called directly by external code, promoting encapsulation.

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
            def __init__(self, config: PipelineConfig):
                super().__init__(config)

            def _create_pipeline_job(self) -> BaseComponent:
                return my_kfp_pipeline
        ```

        Returns:
            A callable KFP pipeline function (which is a BaseComponent instance
            after compilation).
        """
        raise NotImplementedError("Child class must implement _create_pipeline_job method.")

    def submit(
        self, only_validate: bool = False, wait_for_completion: bool = False
    ) -> None:
        """Compiles the KFP pipeline and optionally submits it to Vertex AI for execution.

        This method orchestrates the process of taking a Python-defined KFP pipeline,
        compiling it into a YAML specification, and then using the Vertex AI SDK
        to create and run a PipelineJob.

        Args:
            only_validate: If True, the pipeline will be compiled to a YAML
                           specification, but it will NOT be submitted to Vertex AI.
                           Useful for checking pipeline syntax and structure locally.
            wait_for_completion: If True, the method will block until the submitted
                                 pipeline run finishes (either successfully or with a failure).
                                 This is useful for synchronous execution or debugging.
        """
        logger.info("Setting up Kubeflow pipeline job for submission.")

        # 1. Get the KFP pipeline function from the child class implementation
        pipeline_func = self._create_pipeline_job()

        # 2. Compile the KFP pipeline function into a YAML specification
        # The YAML file defines the pipeline's structure, components, and dependencies.
        pipeline_spec_path = f"/tmp/{self.config.pipeline_display_name}.yaml"
        compiler.Compiler().compile(pipeline_func, pipeline_spec_path)
        logger.info(f"Pipeline compiled to: {pipeline_spec_path}")

        if not only_validate:
            logger.info(f"Submitting pipeline '{self.config.pipeline_display_name}' to Vertex AI.")

            # 3. Create a Vertex AI PipelineJob instance
            # This object represents a single, immediate execution of your compiled pipeline.
            # It encapsulates all the necessary information for Vertex AI to run the pipeline
            job = aiplatform.PipelineJob(
                display_name=self.config.pipeline_display_name, # A human-readable name for this specific pipeline run.
                template_path=pipeline_spec_path,  # The local path to the compiled KFP YAML file. The SDK uploads this.
                pipeline_root=self.config.pipeline_root,  # The GCS URI where all pipeline artifacts (outputs, logs) will be stored.
                parameter_values=self.config.parameter_values,  # Optional: Runtime parameters for the KFP pipeline.
                                                                # These override default parameter values defined in the KFP pipeline function.
                input_artifacts=None,  # Optional: A dictionary mapping artifact names to their GCS URIs.
                                       # Allows injecting existing artifacts into the pipeline run.
                enable_caching=self.config.enable_caching,  # Boolean. If True, Vertex AI reuses results from previous identical component runs.
                                                            # Set to False during development to ensure every step re-executes.
                encryption_spec_key_name=None,  # Optional: Cloud KMS key name for encrypting pipeline artifacts (CMEK).
                labels={**{"experiment": self.config.experiment_name}, **self.config.labels},  # Key-value pairs for organizing and filtering pipeline jobs.
                                                                                                # Merges base experiment label with any additional labels from config.
                project=self.env.gcp.project_id,  # The Google Cloud project ID where this pipeline job will run.
                                                  # If not provided, it defaults to the project set during `aiplatform.init()`.
                location=self.env.gcp.location,  # The Google Cloud region where this pipeline job will run.
                                                  # If not provided, it defaults to the location set during `aiplatform.init()`.
                failure_policy=self.config.failure_policy,  # Optional: Defines behavior on task failure. E.g., "fast_fail" (stop immediately) or "continue".
            )

            # 4. Submit the PipelineJob to Vertex AI
            job.submit()
            logger.info(f"Submitted pipeline job: {job.resource_name}")
            logger.info(f"View job in console: https://console.cloud.google.com/vertex-ai/locations/"
                        f"{self.env.gcp.location}/pipelines/runs/{job.name}?project={self.env.gcp.project_id}")


            if wait_for_completion:
                logger.info("Waiting for pipeline completion...")
                # Blocks until the pipeline run finishes.
                job.wait() # type: ignore # mypy ignores this untyped call
                logger.info(
                    f"Pipeline '{job.display_name}' completed with state: {job.state}"
                )
        else:
            logger.info("Validation completed, not submitting pipeline.")

    def schedule(self, cron_expression: str) -> None:
        """Schedules the pipeline using GCP Vertex AI Pipeline Schedules.

        This method allows you to set up recurring executions of your pipeline
        based on a cron expression. It first creates a PipelineJob definition
        that acts as a template, and then wraps it in a PipelineJobSchedule.

        Why create another PipelineJob here instead of scheduling the one from `submit`?
        --------------------------------------------------------------------------------
        The `submit` function creates an `aiplatform.PipelineJob` object that represents
        a *single, immediate execution* of a pipeline. Once that execution is done,
        that specific `PipelineJob` instance has fulfilled its purpose.

        A Vertex AI Pipeline Schedule, however, defines a *template for future executions*.
        It doesn't schedule a past or currently running job. Instead, it needs a blueprint
        of *what* pipeline to run *each time the schedule triggers*. The `pipeline_job_instance`
        created within this `schedule` method serves precisely this purpose: it's the
        template that the scheduler will use to launch new pipeline runs repeatedly.

        In essence:
        - `submit`: "Run this pipeline *now*, once."
        - `schedule`: "Run this pipeline *repeatedly* according to this cron, using this
                      `PipelineJob` as the blueprint for each new run."

        Args:
            cron_expression: A cron expression string that defines the frequency
                             and timing of the scheduled pipeline runs (e.g., "0 0 * * *" for daily at midnight UTC).
        """
        logger.info("Setting up pipeline schedule.")

        # 1. Get the KFP pipeline function from the child class implementation
        pipeline_func = self._create_pipeline_job()

        # 2. Compile the KFP pipeline function into a YAML specification
        pipeline_spec_path = f"/tmp/{self.config.pipeline_display_name}.yaml"
        compiler.Compiler().compile(pipeline_func, pipeline_spec_path)
        logger.info(f"Pipeline compiled to: {pipeline_spec_path}")

        # 3. Create a Vertex AI PipelineJob instance (this defines the job that will be scheduled)
        # This PipelineJob object serves as the template for each run created by the schedule.
        pipeline_job_instance = aiplatform.PipelineJob(
            display_name=self.config.pipeline_display_name, # A human-readable name for the pipeline runs created by this schedule.
            template_path=pipeline_spec_path,  # The local path to the compiled KFP YAML file. The SDK uploads this.
            pipeline_root=self.config.pipeline_root,  # The GCS URI where all pipeline artifacts (outputs, logs) will be stored.
            project=self.env.gcp.project_id,  # The Google Cloud project ID where scheduled pipeline jobs will run.
            location=self.env.gcp.location,  # The Google Cloud region where scheduled pipeline jobs will run.
            labels={**{"experiment": self.config.experiment_name}, **self.config.labels},  # Labels for organization and tracking of scheduled runs.
            enable_caching=self.config.enable_caching,  # Caching behavior for scheduled runs. Set to True for cost savings on repeated runs.
            parameter_values=self.config.parameter_values, # Runtime parameters for the KFP pipeline template.
            failure_policy=self.config.failure_policy, # Defines behavior on task failure for scheduled runs.
            # Other optional PipelineJob parameters can be set here if needed
        )

        # 4. Create a PipelineJobSchedule instance
        # This object defines the schedule itself, linking it to the PipelineJob template.
        pipeline_job_schedule_instance = PipelineJobSchedule(
            pipeline_job=pipeline_job_instance,  # The PipelineJob template to run repeatedly.
            display_name=f"{self.config.pipeline_display_name}-schedule",  # A unique name for the schedule itself (not the individual runs).
            # credentials=None, # Credentials are typically handled by aiplatform.init() or inherited from the environment.
            # project=None,     # Project is derived from the pipeline_job_instance.
            # location=None,    # Location is derived from the pipeline_job_instance.
        )

        # 5. Call create() on the PipelineJobSchedule instance to activate the schedule
        # The 'cron' parameter is the primary configuration for the schedule's timing.
        pipeline_job_schedule_instance.create(
            cron=cron_expression,
            # Optional: max_concurrent_run_count, max_run_count, start_time, end_time
        )
        logger.info(f"Created schedule: {pipeline_job_schedule_instance.name}")
        logger.info(f"View schedule in console: https://console.cloud.google.com/vertex-ai/locations/{self.env.gcp.location}/pipeline-job-schedules/{pipeline_job_schedule_instance.name}?project={self.env.gcp.project_id}")