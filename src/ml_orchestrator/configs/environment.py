"""Dataclass to load and hold general environment variables for GCP."""

import os
from dataclasses import dataclass, field

# The deploy environment names (adapt as needed)
DEPLOY_ENV_NAMES: list[str] = ["dev", "stg", "prod"]


@dataclass(frozen=True)
class GCPConfig:
    """GCP-related configuration."""

    project_id: str | None = os.environ.get("GOOGLE_PROJECT_ID")
    location: str | None = os.environ.get("GOOGLE_LOCATION", "us-central1")  # Equivalent to region
    secret_manager_project_id: str | None = os.environ.get("SECRET_MANAGER_PROJECT_ID")
    service_account_email: str | None = os.environ.get("GOOGLE_SERVICE_ACCOUNT_EMAIL")
    service_account_key_path: str | None = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    workload_identity_provider: str | None = os.environ.get("WORKLOAD_IDENTITY_PROVIDER")  # For GKE
    bucket_name: str | None = os.environ.get("GOOGLE_BUCKET_NAME")
    artifact_registry_host: str | None = os.environ.get("ARTIFACT_REGISTRY_HOST", "us-central1-docker.pkg.dev")
    artifact_registry_repo: str | None = os.environ.get("ARTIFACT_REGISTRY_REPO")


@dataclass(frozen=True)
class GitConfig:
    """Git-related configuration."""

    token: str | None = os.environ.get("GIT_TOKEN")
    username: str | None = os.environ.get("GIT_USERNAME", "token")


@dataclass(frozen=True)
class BigQueryConfig:
    """BigQuery-related configuration."""

    dataset: str | None = os.environ.get("BIGQUERY_DATASET")
    table: str | None = os.environ.get("BIGQUERY_TABLE")  # Optional, can be extended


@dataclass(frozen=True)
class Env:
    """Loads all environment variables into a predefined set of properties."""  # pylint: disable=too-many-instance-attributes

    team_prefix: str | None = os.environ.get("TEAM_PREFIX")
    deploy_env: str | None = os.environ.get("DEPLOY_ENVIRONMENT")
    gcp: GCPConfig = field(default_factory=GCPConfig)
    git: GitConfig = field(default_factory=GitConfig)
    bigquery: BigQueryConfig = field(default_factory=BigQueryConfig)

    def validate(self) -> bool:
        """Validate required vars."""
        if not self.gcp.project_id:
            raise ValueError("GOOGLE_PROJECT_ID is required.")
        if self.deploy_env and self.deploy_env not in DEPLOY_ENV_NAMES:
            raise ValueError(f"Invalid deploy_env: {self.deploy_env}. Must be one of {DEPLOY_ENV_NAMES}.")
        return True
