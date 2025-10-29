"""Package for Machine Learning Orchestrator.

Contains variable PROJECT_NAME.
"""

import importlib.metadata

from .cli import get_pipeline_commands_and_arguments, run_pipeline_command
from .configs import Env, PipelineSettings, TaskSettings, VarProjectResourceNames
from .configs.abstractions import BaseVarTemplateComponent, VarTemplateComponent
from .pipeline_assembly import GenericPipeline
from .project import GCPProject
from .task_utils import apply_task_settings, with_gpu

PROJECT_NAME = "ML-ORCHESTRATOR"

try:
    __version__ = importlib.metadata.version(PROJECT_NAME)
except importlib.metadata.PackageNotFoundError:
    # If the package is not installed, we can't determine the version.
    # This is common during development.
    __version__ = "0.0.0.dev0"

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
    "BaseVarTemplateComponent",
    "VarTemplateComponent",
    "get_pipeline_commands_and_arguments",
    "run_pipeline_command",
]
