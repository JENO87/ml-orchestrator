"""Dataclass to load and hold general environment variables for GCP."""

import os
from dataclasses import dataclass

# The deploy environment names (adapt as needed)
DEPLOY_ENV_NAMES: list[str] = ["dev", "stg", "prod"]


@dataclass(frozen=True)
class Env:
    """Loads all environment variables into a predefined set of properties."""

    # Team prefix/slug, e.g., "mlteam01"
    team_prefix: str | None = os.environ.get("TEAM_PREFIX")

    # Project/Workspace
    project_id: str | None = os.environ.get("GOOGLE_PROJECT_ID")
    location: str | None = os.environ.get("GOOGLE_LOCATION", "us-central1")  # Equivalent to region

    # Secret Manager (new: for secure secrets, defaults to project_id)
    secret_manager_project_id: str | None = os.environ.get("SECRET_MANAGER_PROJECT_ID")

    # Authentication (Service Account, equivalent to Service Principal/Managed Identity)
    service_account_email: str | None = os.environ.get("GOOGLE_SERVICE_ACCOUNT_EMAIL")
    service_account_key_path: str | None = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    workload_identity_provider: str | None = os.environ.get("WORKLOAD_IDENTITY_PROVIDER")  # For GKE

    # Storage (Cloud Storage, equivalent to Azure Storage)
    bucket_name: str | None = os.environ.get("GOOGLE_BUCKET_NAME")

    # Container Registry (Artifact Registry, equivalent to ACR)
    artifact_registry_host: str | None = os.environ.get("ARTIFACT_REGISTRY_HOST", "us-central1-docker.pkg.dev")
    artifact_registry_repo: str | None = os.environ.get("ARTIFACT_REGISTRY_REPO")

    # Git (e.g., for GitHub or Cloud Source Repositories, equivalent to GitLab)
    git_token: str | None = os.environ.get("GIT_TOKEN")
    git_username: str | None = os.environ.get("GIT_USERNAME", "token")

    # BigQuery (equivalent to Dremio for data querying)
    bigquery_dataset: str | None = os.environ.get("BIGQUERY_DATASET")
    bigquery_table: str | None = os.environ.get("BIGQUERY_TABLE")  # Optional, can be extended

    # Deploy Environment
    deploy_env: str | None = os.environ.get("DEPLOY_ENVIRONMENT")

    # Optional validation method (override in subclasses)
    def validate(self) -> bool:
        """Validate required vars. Subclasses can extend for custom checks."""
        if not self.project_id:
            raise ValueError("GOOGLE_PROJECT_ID is required.")
        if self.deploy_env and self.deploy_env not in DEPLOY_ENV_NAMES:
            raise ValueError(f"Invalid deploy_env: {self.deploy_env}. Must be one of {DEPLOY_ENV_NAMES}.")
        # Add more checks as needed, e.g., for auth
        return True
