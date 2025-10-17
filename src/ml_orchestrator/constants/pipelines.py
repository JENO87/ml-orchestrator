from dataclasses import dataclass, field

from .environments import DEPLOY_ENV_NAMES

DEFAULT_BUCKET_NAME = "your-bucket"

@dataclass
class PipelineConfig:
    """Pipeline resource names and config."""
    slug: str
    deploy_env: str
    pipeline_root: str = "gs://your-bucket/pipeline-root"
    experiment_name: str = "ml-orchestrator-experiment"

    bucket_name: str = field(init=False)
    enable_caching: bool = field(default=True, init=False)

    def __post_init__(self) -> None:
        """Initialize dependent fields."""
        self.deploy_env = self.deploy_env.lower()
        if self.deploy_env not in DEPLOY_ENV_NAMES:
            raise ValueError(f"deploy_env must be one of {DEPLOY_ENV_NAMES}")
        self.bucket_name = f"{self.deploy_env}-{self.slug}-bucket"