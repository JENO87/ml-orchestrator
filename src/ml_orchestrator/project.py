"""Provide GCP connection handling for Vertex AI and related services."""

import os
import re
from datetime import datetime
from typing import Optional

import google.auth
from google.api_core.exceptions import NotFound

# isort: skip
from google.cloud import (
    aiplatform,
    secretmanager,
    storage,  # type: ignore
)
from google.oauth2 import service_account
from loguru import logger

from ml_orchestrator.configs.environment import DEPLOY_ENV_NAMES, Env
from ml_orchestrator.configs.naming import VarProjectResourceNames

PROJECT_ID_PATTERN = re.compile(r"^(.*)-(dev|stg|prod)$")  # Example pattern for project naming


class GCPProject:
    """Setup connection to GCP (Vertex AI, etc.)."""

    _prefix: str
    _deploy_env: str
    _credentials: google.auth.credentials.Credentials | None = None
    _storage_client: storage.Client | None = None
    _secret_manager_client: secretmanager.SecretManagerServiceClient | None = None

    def __init__(self, from_config: bool = False):
        """Initialize GCPProject.

        Parameters
        ----------
        from_config: bool, optional
            Load from a config file (future extension; currently unused).
        """
        self.from_config = from_config

        self.env = Env()
        self.env.validate()  # Ensure env is ready

        if GCPProject._credentials is None:
            logger.debug("Initialize GCP credentials...")
            GCPProject._credentials = self._get_credentials()

        aiplatform.init(
            project=self.env.gcp.project_id,
            location=self.env.gcp.location,
            credentials=GCPProject._credentials,
        )

        GCPProject._storage_client = storage.Client(credentials=GCPProject._credentials)

        # New: Initialize Secret Manager if project_id available
        secret_project = self.env.gcp.secret_manager_project_id or self.env.gcp.project_id
        if secret_project:
            logger.debug(f"Initialize Secret Manager client for project {secret_project}")
            GCPProject._secret_manager_client = secretmanager.SecretManagerServiceClient(
                credentials=GCPProject._credentials
            )
        else:
            logger.warning("No secret_manager_project_id or project_id set; skipping Secret Manager init.")

        self._prefix, self._deploy_env = self._get_prefix_and_deploy_env()
        self.resources = VarProjectResourceNames(prefix=self._prefix, deploy_env=self._deploy_env)

    @property
    def credentials(self) -> google.auth.credentials.Credentials | None:
        """Get the GCP credentials."""
        return GCPProject._credentials

    @property
    def storage_client(self) -> storage.Client | None:
        """Get the Cloud Storage client."""
        return GCPProject._storage_client

    @property
    def secret_manager_client(self) -> secretmanager.SecretManagerServiceClient | None:
        """Get the Secret Manager client."""
        return GCPProject._secret_manager_client

    @property
    def prefix(self) -> str:
        """Get the prefix (e.g., team slug)."""
        return self._prefix

    @property
    def deploy_env(self) -> str:
        """Get the deploy environment."""
        return self._deploy_env

    def _get_credentials(self) -> google.auth.credentials.Credentials:
        """Get GCP credentials."""
        if self.env.gcp.service_account_key_path:
            logger.info("Using service account key from GOOGLE_APPLICATION_CREDENTIALS.")
            creds: service_account.Credentials = service_account.Credentials.from_service_account_file(
                self.env.gcp.service_account_key_path
            )
            return creds
        logger.info("Using Application Default Credentials (ADC).")
        creds, _ = google.auth.default()
        if not creds:
            raise ValueError("Could not obtain application default credentials.")
        return creds

    def get_secret(
        self,
        secret_name: str,
        version: str = "latest",
        fallback_env_var: str | None = None,
    ) -> Optional[str]:
        """Retrieve a secret from Secret Manager, with optional env var fallback."""
        if self.secret_manager_client is None:
            logger.warning("Secret Manager client not initialized; using fallback if available.")
        else:
            project_id = self.env.gcp.secret_manager_project_id or self.env.gcp.project_id
            if project_id:
                secret_path = self.secret_manager_client.secret_version_path(
                    project=project_id,
                    secret=secret_name,
                    secret_version=version,
                )
                try:
                    response = self.secret_manager_client.access_secret_version(request={"name": secret_path})
                    return response.payload.data.decode("UTF-8")
                except NotFound:
                    logger.warning(f"Secret '{secret_name}' not found in Secret Manager.")
            else:
                logger.warning("No project ID found for Secret Manager.")

        # Fallback to env var
        if fallback_env_var:
            return os.environ.get(fallback_env_var)
        return None

    def get_bucket(self, bucket_name: str | None = None) -> storage.Bucket | None:
        """Get a Cloud Storage bucket (defaults to resources.cloud_storage_bucket)."""
        bucket_name = bucket_name or self.resources.cloud_storage_bucket
        if self.storage_client is None:
            logger.warning("Storage client not initialized.")
            return None
        try:
            bucket = self.storage_client.get_bucket(bucket_name)
            logger.info(f"Bucket '{bucket_name}' found.")
            return bucket
        except NotFound:
            logger.warning(f"Bucket '{bucket_name}' not found.")
            return None

    @staticmethod
    def version_now() -> str:
        """Get a path-friendly version from current UTC datetime."""
        return datetime.utcnow().strftime("%Y-%m-%d-%H-%M-%S-%f")

    def _get_prefix_and_deploy_env(self) -> tuple[str, str]:
        """Get prefix and deploy env from project ID or env vars.

        Assumes project ID like 'prefix-deploy_env' if patterned.
        """
        prefix = self.env.team_prefix
        deploy_env = self.env.deploy_env

        if self.env.gcp.project_id:
            match = re.fullmatch(PROJECT_ID_PATTERN, self.env.gcp.project_id)
            if match:
                prefix, deploy_env = match.group(1, 2)
                deploy_env = deploy_env.lower()

        if prefix is None or deploy_env is None or deploy_env not in DEPLOY_ENV_NAMES:
            raise ValueError("Could not determine prefix or valid deploy_env from env vars or project ID.")

        return prefix, deploy_env
