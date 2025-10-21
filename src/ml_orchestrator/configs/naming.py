"""Provide functions and classes for GCP resource names."""

from dataclasses import dataclass, field

from ml_orchestrator.configs.environment import DEPLOY_ENV_NAMES

WORKSPACE_DEFAULT_GCS_BUCKET: str = "workspacegcpbucket"


@dataclass
class VarProjectResourceNames:
    """Various names of GCP resources.

    Resource names are generated from a prefix (e.g., team prefix) and deploy
    environment.

    Parameters
    ----------
    prefix: str
        A prefix like team slug, e.g., "mlteam".
    deploy_env: str
        The deploy environment, e.g., "dev", "stg", "prod".

    Attributes
    ----------
    gke_cluster: str
        GKE cluster name, e.g., "dev-mlteam-gke".
    artifact_registry: str
        Artifact Registry repo name, e.g., "dev-mlteam-repo".
    cloud_storage_bucket: str
        Cloud Storage bucket, e.g., "dev-mlteam-bucket".
    bigquery_dataset: str
        BigQuery dataset, e.g., "dev_mlteam_dataset".
    vertex_ai_pipeline_root: str
        Vertex AI pipeline root path, e.g., "gs://dev-mlteam-bucket/pipelines".
    """

    prefix: str
    deploy_env: str

    gke_cluster: str = field(init=False)
    artifact_registry: str = field(init=False)
    cloud_storage_bucket: str = field(init=False)
    bigquery_dataset: str = field(init=False)
    vertex_ai_pipeline_root: str = field(init=False)

    def __post_init__(self) -> None:
        """Initialize field values that depend on prefix and deploy_env."""
        self.deploy_env = self.deploy_env.lower()
        if self.deploy_env not in DEPLOY_ENV_NAMES:
            raise ValueError(f"deploy_env parameter ({self.deploy_env}) needs to be one of of {DEPLOY_ENV_NAMES}")

        self.gke_cluster = f"{self.deploy_env}-{self.prefix}-gke"
        self.artifact_registry = f"{self.deploy_env}-{self.prefix}-repo"
        self.cloud_storage_bucket = f"{self.deploy_env}-{self.prefix}-bucket"
        self.bigquery_dataset = f"{self.deploy_env}_{self.prefix}_dataset"
        self.vertex_ai_pipeline_root = f"gs://{self.cloud_storage_bucket}/pipelines"
