from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional


# --- Abstract Contract for Overall Pipeline Settings ---
class PipelineSettings(ABC):
    """An abstract contract for overall pipeline settings.

    Concrete implementations must provide values for the abstract properties.
    This class also provides default values for optional PipelineJob parameters,
    which can be overridden by concrete implementations.
    """

    @property
    @abstractmethod
    def pipeline_display_name(self) -> str:
        """The user-facing name of the pipeline in Vertex AI."""
        pass

    @property
    @abstractmethod
    def pipeline_description(self) -> str:
        """A brief description of the pipeline."""
        pass

    @property
    @abstractmethod
    def pipeline_root(self) -> str:
        """GCS path for pipeline artifacts (e.g., 'gs://my-bucket/pipelines')."""
        pass

    @property
    @abstractmethod
    def experiment_name(self) -> str:
        """The name of the Vertex AI experiment to group runs under."""
        pass

    # Optional PipelineJob parameters with default property implementations
    @property
    def enable_caching(self) -> bool:
        """Whether to enable caching for pipeline steps. Defaults to True."""
        return True # Default to True for cost savings and faster reruns

    @property
    def parameter_values(self) -> Optional[Dict[str, Any]]:
        """Runtime parameters for the KFP pipeline. Defaults to None."""
        return None # Runtime parameters for the KFP pipeline

    @property
    def input_artifacts(self) -> Optional[Dict[str, str]]:
        """Input artifacts for the pipeline. Defaults to None."""
        return None

    @property
    def encryption_spec_key_name(self) -> Optional[str]:
        """Cloud KMS key name for encrypting pipeline artifacts (CMEK). Defaults to None."""
        return None

    @property
    def labels(self) -> Dict[str, str]:
        """Additional labels for the PipelineJob. Defaults to an empty dictionary."""
        return {} # Additional labels for the PipelineJob

    @property
    def failure_policy(self) -> Optional[str]:
        """Defines behavior on task failure (e.g., 'fast_fail' or 'continue'). Defaults to None."""
        return None # e.g., "fast_fail" or "continue"

# --- Base Class for Individual Task (Component) Settings ---
@dataclass(frozen=True)
class TaskSettings:
    """A base dataclass for standard pipeline task settings."""

    display_name: str
    cpu_limit: str = "1"
    memory_limit: str = "4G"
    enable_caching: bool = True