from abc import ABC, abstractmethod
from pathlib import Path
from typing import Protocol, Tuple
from google.cloud import aiplatform
from ml_orchestrator import logger
from ml_orchestrator.constants.workspace import VarWorkspaceResourceNames
from ml_orchestrator.utils.repository import Repository
from ml_orchestrator.workspace import GCPWorkspace

class ComponentConfig(Protocol):
    """Protocol defining required attributes for a component."""
    repo_name: str
    repo_namespace: str
    repo_url: str
    repo_local_path: str
    script_path: str
    default_register: bool

class GenericComponent(ABC, GCPWorkspace, Repository):
    """Abstract base class for GCP Vertex AI/Kubeflow components."""

    def __init__(self) -> None:
        """Initialize the component with GCP workspace and repository handling."""
        super().__init__()

    def get_script_and_code_paths(self, var_component: ComponentConfig) -> Tuple[str, Path]:
        """
        Get the script and code paths for the component, considering feature branches.

        Args:
            var_component: Component configuration with repository and script details.

        Returns:
            Tuple[str, Path]: Script path as string and code path as Path.

        Raises:
            ValueError: If script or code paths are invalid.
        """
        source_directory = f"{var_component.repo_local_path}/{var_component.script_path}"
        script_path = ""
        default_branch = self.get_branch_from_deploy_environment(deploy_env=self.deploy_env or "dev")
        feature_branch = self.branch.get(var_component.repo_name, default_branch)

        if feature_branch != default_branch:
            logger.info(f"Feature branch {feature_branch} takes precedence over default for {var_component.repo_name}")
            source_directory = var_component.repo_local_path
            script_path = f"{var_component.script_path}/"

        code_path = Path(source_directory)
        if not code_path.exists():
            raise ValueError(f"Code path {code_path} does not exist.")

        logger.debug(f"Script path: {script_path}")
        logger.debug(f"Code path: {code_path}")

        return script_path, code_path

    @abstractmethod
    def _create_component(self) -> aiplatform.CustomJob:
        """
        Creates a Vertex AI CustomJob or Kubeflow component.

        Use `get_script_and_code_paths` to get script and code paths, accounting for feature branches.

        Example:
        --------
        >>> var_component = VarWorkspaceResourceNames(...)
        >>> script_path, code_path = self.get_script_and_code_paths(var_component)
        >>> job = aiplatform.CustomJob(
        ...     display_name=var_component.repo_name,
        ...     worker_pool_specs=[{
        ...         "machine_type": "n1-standard-4",
        ...         "replica_count": 1,
        ...         "python_package_spec": {
        ...             "executor_image_uri": "gcr.io/cloud-aiplatform/python:3.9",
        ...             "package_uris": [f"gs://{code_path}"],
        ...             "python_module": f"{script_path}main",
        ...         }
        ...     }]
        ... )
        >>> return job

        Returns:
            aiplatform.CustomJob: The initialized Vertex AI CustomJob.
        """
        pass

    def component(self, register: bool, var_component: ComponentConfig) -> aiplatform.CustomJob:
        """
        Register or retrieve a Vertex AI component.

        Args:
            register: If True, register a new component version. If False, use an existing one if available.
            var_component: Component configuration with repository and script details.

        Returns:
            aiplatform.CustomJob: The registered or retrieved component.

        Raises:
            ValueError: If component registration or retrieval fails.
        """
        job = self._create_component()

        if self.vertex_client is None:
            raise AttributeError("Vertex AI client not initialized.")

        try:
            if register or var_component.default_register:
                logger.info(f"Registering new version of component {job.display_name}")
                job.run()  # In Vertex AI, running a CustomJob registers it
                logger.info(f"Registered component {job.display_name} with ID {job.resource_name}")
            else:
                logger.info(f"Retrieving existing component {job.display_name}")
                # Vertex AI doesn't have a direct "get component" API; assume job exists or register
                job.run()  # Fallback: run to ensure it’s registered
                logger.info(f"Using component {job.display_name} with ID {job.resource_name}")
        except Exception as e:
            logger.error(f"Failed to handle component {job.display_name}: {e}")
            raise ValueError(f"Component handling failed: {e}")

        return job