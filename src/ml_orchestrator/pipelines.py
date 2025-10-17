# ml_orchestrator/pipeline/pipeline.py
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Optional
import kfp
import kfp.dsl as dsl
from google.cloud import aiplatform
from google.cloud.scheduler_v1 import Job, CreateJobRequest, CloudSchedulerClient
from ml_orchestrator import logger
from ml_orchestrator.utils.repository import Repository
from ml_orchestrator.workspace import GCPWorkspace
from ml_orchestrator.constants.workspace import WORKSPACE_DEFAULT_GCS_BUCKET

class GenericPipeline(ABC, GCPWorkspace, Repository):
    """Abstract base class for Kubeflow Pipelines on GCP Vertex AI."""

    def __init__(self, register: bool = False, gcs_bucket: str = WORKSPACE_DEFAULT_GCS_BUCKET) -> None:
        """
        Initialize with GCP workspace and repository handling.

        Args:
            register: If True, register all components. If False, only register components with default_register=True.
            gcs_bucket: GCS bucket for pipeline artifacts.
        """
        super().__init__()
        self.register = register
        self.wipe_repository_path: bool = False
        self.gcs_bucket = gcs_bucket
        self.vertex_client = aiplatform.PipelineJob

    @abstractmethod
    def _create_pipeline_job(self) -> dsl.Pipeline:
        """
        Define a Kubeflow Pipeline.

        Returns:
            dsl.Pipeline: The Kubeflow pipeline definition.
        """
        pass

    def submit(
        self,
        experiment_name: str,
        only_validate: bool,
        wait_for_completion: bool,
        wipe_repository_path: bool,
        branch: Dict[str, str],
    ) -> None:
        """
        Submit a Kubeflow Pipeline to Vertex AI.

        Args:
            experiment_name: Name of the experiment for tracking.
            only_validate: If True, validate the pipeline without submitting.
            wait_for_completion: If True, wait for the pipeline to complete.
            wipe_repository_path: If True, wipe existing repository paths before cloning.
            branch: Dictionary mapping repository names to feature branches.

        Raises:
            ValueError: If pipeline validation or submission fails.
        """
        logger.info("Setting up Kubeflow pipeline")
        self.wipe_repository_path = wipe_repository_path
        if branch:
            self.branch = branch

        pipeline_func = self._create_pipeline_job()
        pipeline_spec_path = f"/tmp/{pipeline_func.__name__}.yaml"
        kfp.compiler.Compiler().compile(pipeline_func, pipeline_spec_path)

        logger.info(f"Validating pipeline {pipeline_func.__name__}")
        try:
            kfp.Client().create_run_from_pipeline_package(pipeline_spec_path, validate_only=True)
            logger.info("Pipeline validated successfully")
        except Exception as e:
            logger.error(f"Pipeline validation failed: {e}")
            raise ValueError(f"Pipeline validation failed: {e}")

        if not only_validate:
            logger.info(f"Submitting pipeline {pipeline_func.__name__} for experiment {experiment_name}")
            job = aiplatform.PipelineJob(
                display_name=pipeline_func.__name__,
                template_path=pipeline_spec_path,
                pipeline_root=f"gs://{self.gcs_bucket}/pipelines",
                project=self.project_id,
                location=self.region,
                labels={"experiment": experiment_name},
                service_account=self.service_account,
            )
            job.submit()
            logger.info(f"Submitted pipeline job: {job.resource_name}")

            if wait_for_completion:
                logger.info("Waiting for pipeline completion")
                job.wait()
                logger.info(f"Pipeline {job.display_name} completed with state: {job.state}")
        else:
            logger.info("Validation completed, not submitting pipeline")

    def schedule(
        self,
        job_name: str,
        name: str,
        expression: str,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> None:
        """
        Schedule a pipeline using GCP Cloud Scheduler.

        Args:
            job_name: The Vertex AI pipeline job name or ID.
            name: The name of the schedule.
            expression: Cron expression (e.g., "0 0 * * *").
            display_name: Display name for the schedule.
            description: Description of the schedule.

        Raises:
            ValueError: If scheduling fails.
        """
        logger.info(f"Setting up schedule for pipeline job: {job_name}")
        client = CloudSchedulerClient()
        parent = f"projects/{self.project_id}/locations/{self.region}"

        job = Job(
            name=f"{parent}/jobs/{name}",
            description=description or f"Schedule for pipeline {job_name}",
            schedule=expression,
            time_zone="Europe/Paris",
            http_target={
                "http_method": "POST",
                "uri": f"https://{self.region}-aiplatform.googleapis.com/v1/projects/{self.project_id}/locations/{self.region}/pipelineJobs/{job_name}:run",
                "oidc_token": {
                    "service_account_email": self.service_account,
                },
            },
        )

        try:
            request = CreateJobRequest(parent=parent, job=job)
            response = client.create_job(request=request)
            logger.info(f"Created schedule: {response.name}")
        except Exception as e:
            logger.error(f"Failed to create schedule: {e}")
            raise ValueError(f"Scheduling failed: {e}")