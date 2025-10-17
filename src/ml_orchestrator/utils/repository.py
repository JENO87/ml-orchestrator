import os
from pathlib import Path
from typing import NamedTuple, Protocol, Dict, List
import git
import shutil
from ml_orchestrator import logger
from ml_orchestrator.constants.environments import Env

class VarComponentType(Protocol):
    """Protocol defining required attributes for a repository component."""
    repo_name: str
    repo_namespace: str
    repo_url: str
    repo_local_path: str

class RepositoryConfig(NamedTuple):
    """Tuple-like object with repository fields accessible by attribute lookup."""
    name: str
    namespace: str
    url: str
    local_path: str
    branch: str
    username: str
    password: str  # Use secrets; fetched securely

class RepositoryError(Exception):
    """Custom exception for repository-related errors."""
    pass

class Repository:
    """Manages repository configuration and cloning operations."""
    
    # Configurable branch mappings
    _DEFAULT_BRANCH_MAP = {
        "dev": "development",
        "stg": "staging",
        "prod": "main"
    }

    def __init__(self):
        """Initialize Repository with instance-specific state."""
        self._branch: Dict[str, str] = {}
        self._wipe_repository_path: bool = False

    @property
    def branch(self) -> Dict[str, str]:
        """Get the branch mapping dictionary."""
        return self._branch

    @branch.setter
    def branch(self, branch: Dict[str, str]) -> None:
        """Set the branch mapping dictionary."""
        self._branch = branch

    @property
    def wipe_repository_path(self) -> bool:
        """Get the wipe repository path setting."""
        return self._wipe_repository_path

    @wipe_repository_path.setter
    def wipe_repository_path(self, wipe_repository_path: bool) -> None:
        """Set the wipe repository path setting."""
        self._wipe_repository_path = wipe_repository_path

    def get_repo(self, var_component: VarComponentType) -> RepositoryConfig:
        """
        Get the repository configuration for cloning.

        Args:
            var_component: Object with repository details (name, namespace, url, local_path).

        Returns:
            RepositoryConfig: Configuration object for the repository.

        Raises:
            RepositoryError: If required configuration (e.g., GIT_TOKEN) is missing.
        """
        env = Env()
        deploy_env = env.deploy_env or "dev"
        
        # Get default branch from deploy environment
        default_branch = self.get_branch_from_deploy_environment(deploy_env)
        
        # Use feature branch if specified, else default branch
        branch = self.branch.get(var_component.repo_name, default_branch)
        
        # Fetch git token from environment (replace with secure secret management in production)
        git_token = os.getenv("GIT_TOKEN")
        if not git_token:
            raise RepositoryError("GIT_TOKEN not found in environment variables.")

        return RepositoryConfig(
            name=var_component.repo_name,
            namespace=var_component.repo_namespace,
            url=var_component.repo_url,
            local_path=var_component.repo_local_path,
            branch=branch,
            username=str(env.git_username),
            password=git_token,
        )

    def get_branch_from_deploy_environment(self, deploy_env: str) -> str:
        """
        Get the repository branch based on the deployment environment.

        Args:
            deploy_env: The deployment environment (e.g., 'dev', 'stg', 'prod').

        Returns:
            str: The branch corresponding to the deployment environment.

        Raises:
            RepositoryError: If the deployment environment is unknown.
        """
        logger.info(f"Determining branch for deploy environment: {deploy_env}")
        deploy_env_lowercase = deploy_env.lower()
        
        branch = self._DEFAULT_BRANCH_MAP.get(deploy_env_lowercase)
        if not branch:
            raise RepositoryError(f"Unknown deploy environment: {deploy_env}")
        
        logger.debug(f"Selected branch: {branch}")
        return branch

    @staticmethod
    def clone_repository(repository: RepositoryConfig, wipe: bool = False) -> None:
        """
        Clone a git repository to the specified local path.

        Args:
            repository: RepositoryConfig object with repository details.
            wipe: If True, remove existing directory before cloning.

        Raises:
            RepositoryError: If cloning fails due to git errors or invalid configuration.
        """
        repository_path = Path(repository.local_path)

        # Wipe existing directory if requested
        if repository_path.is_dir() and wipe:
            logger.warning(f"Wiping existing local clone at {repository_path} for {repository.name}")
            try:
                shutil.rmtree(repository_path)
            except OSError as e:
                raise RepositoryError(f"Failed to wipe repository path {repository_path}: {e}")

        # Construct URL without embedding credentials
        repo_url = f"https://{repository.url}/{repository.namespace}/{repository.name}.git"
        logger.info(f"Cloning {repository.name} (branch: {repository.branch}) to {repository_path}")

        try:
            # Use gitpython's auth support instead of embedding credentials
            repo = git.Repo.clone_from(
                url=repo_url,
                to_path=repository_path,
                branch=repository.branch,
                config=f"http.extraHeader=Authorization: Basic {repository.username}:{repository.password}"
            )
            logger.info(f"Successfully cloned {repository.name} to {repository_path}")
        except git.GitCommandError as e:
            logger.error(f"Failed to clone {repository.name}: {e}")
            raise RepositoryError(f"Cloning failed for {repository.name}: {e}")

    def clone_repositories(self, repositories: List[RepositoryConfig]) -> None:
        """
        Clone multiple repositories.

        Args:
            repositories: List of RepositoryConfig objects to clone.

        Raises:
            RepositoryError: If cloning any repository fails.
        """
        for repository in repositories:
            self.clone_repository(repository=repository, wipe=self.wipe_repository_path)