from abc import ABC, abstractmethod

from google.cloud import aiplatform
from google.cloud.aiplatform import PipelineJobSchedule
from kfp import compiler
from kfp.dsl.base_component import BaseComponent

from ml_orchestrator import logger
from ml_orchestrator.configs import PipelineConfig
from ml_orchestrator.workspace import GCPProject


class GenericPipeline(ABC, GCPProject):
    """Abstract base class for Kubeflow Pipelines on GCP Vertex AI.

    This class provides the core, reusable logic for submitting and scheduling KFP pipelines on Vertex AI. It is
    designed to be inherited by a specific pipeline implementation in a 'wrapper' repository.

    The user of this class must provide a configuration object that adheres to the 'PipelineConfig' contract.
    """

    def __init__(self, config: PipelineConfig):
        """Initialize the pipeline with GCP workspace and a configuration object.

        Args:
            config: A concrete implementation of AbstractPipelineConfig containing
                    pipeline-specific configuration like names and roots.
        """
        super().__init__()
        self.config = config
        self.vertex_client = aiplatform

    @abstractmethod
    def _create_pipeline_job(self) -> BaseComponent:
        """An abstract method that must be implemented by the child class. This method should define and return a KFP
        pipeline function decorated with '@dsl.pipeline'.

        Returns
        -------
            A callable KFP pipeline function (which is a BaseComponent).
        """
        raise NotImplementedError

    def submit(self, only_validate: bool = False, wait_for_completion: bool = False) -> None:
        """Compiles and submits the KFP pipeline to Vertex AI.

        Args:
            only_validate: If True, compile the pipeline but do not submit it.
            wait_for_completion: If True, wait for the submitted pipeline run to complete.
        """
        logger.info("Setting up Kubeflow pipeline job")

        pipeline_func = self._create_pipeline_job()
        pipeline_spec_path = f"/tmp/{self.config.pipeline_display_name}.yaml"
        compiler.Compiler().compile(pipeline_func, pipeline_spec_path)

        if not only_validate:
            logger.info(f"Submitting pipeline '{self.config.pipeline_display_name}'")
            job = aiplatform.PipelineJob(
                display_name=self.config.pipeline_display_name,
                template_path=pipeline_spec_path,
                pipeline_root=self.config.pipeline_root,
                project=self.env.project_id,
                location=self.env.location,
                labels={"experiment": self.config.experiment_name},
                service_account=self.env.service_account_email,
                enable_caching=False,  # Recommended to set explicitly
            )
            job.submit()
            logger.info(f"Submitted pipeline job: {job.resource_name}")

            if wait_for_completion:
                logger.info("Waiting for pipeline completion...")
                job.wait()
                logger.info(f"Pipeline {job.display_name} completed with state: {job.state}")
        else:
            logger.info("Validation completed, not submitting pipeline.")

    def schedule(self, cron_expression: str) -> None:
        """Schedules the pipeline using GCP Vertex AI Pipeline Schedules.

        Args:
            cron_expression: Cron expression for the schedule (e.g., "0 0 * * *").
        """
        logger.info("Setting up pipeline schedule")
        pipeline_func = self._create_pipeline_job()
        pipeline_spec_path = f"/tmp/{self.config.pipeline_display_name}.yaml"
        compiler.Compiler().compile(pipeline_func, pipeline_spec_path)

        schedule = PipelineJobSchedule.create(
            display_name=self.config.pipeline_display_name,
            cron=cron_expression,
            pipeline_template=pipeline_spec_path,
            pipeline_root=self.config.pipeline_root,
            project=self.env.project_id,
            location=self.env.location,
        )
        logger.info(f"Created schedule: {schedule.name}")
