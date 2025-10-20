from abc import ABC, abstractmethod
from dataclasses import dataclass


# --- Contract for the Overall Pipeline ---
class PipelineConfig(ABC):
    """An abstract contract for overall pipeline configuration."""

    @property
    @abstractmethod
    def pipeline_display_name(self) -> str:
        """The user-facing name of the pipeline in Vertex AI."""
        raise NotImplementedError

    @property
    @abstractmethod
    def pipeline_description(self) -> str:
        """A brief description of the pipeline."""
        raise NotImplementedError

    @property
    @abstractmethod
    def pipeline_root(self) -> str:
        """GCS path for pipeline artifacts. E.g., 'gs://my-bucket/pipelines'."""
        raise NotImplementedError

    @property
    @abstractmethod
    def experiment_name(self) -> str:
        """The name of the Vertex AI experiment to group runs under."""
        raise NotImplementedError


# --- Base Class for Individual Task (Component) Settings ---
@dataclass(frozen=True)
class TaskSettings:
    """A base dataclass for standard pipeline task settings."""

    display_name: str
    cpu_limit: str = "1"
    memory_limit: str = "4G"
    enable_caching: bool = True