"""Package for Machine Learning Orchestrator.

Contains variable PROJECT_NAME.
"""

from .cli import get_pipeline_commands_and_arguments, run_pipeline_command
from .configs import Env, PipelineSettings, TaskSettings, VarProjectResourceNames
from .pipeline_assembly import GenericPipeline
from .project import GCPProject
from .task_utils import apply_task_settings, with_gpu

PROJECT_NAME = "ML-ORCHESTRATOR"
__version__ = "0.1.0"
PROJECT_VERSION = __version__


__all__ = [
    "GCPProject",
    "GenericPipeline",
    "PipelineSettings",
    "TaskSettings",
    "apply_task_settings",
    "with_gpu",
    "Env",
    "VarProjectResourceNames",
    "get_pipeline_commands_and_arguments",
    "run_pipeline_command",
]
