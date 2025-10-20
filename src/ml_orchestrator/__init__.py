"""Package for Machine Learning Orchestrator.

Contains variable PROJECT_NAME.
"""

from datetime import datetime
from pathlib import Path

from loguru import logger
from utils.cli import get_pipeline_commands_and_arguments, run_pipeline_command

from .configs import Env, PipelineConfig, TaskSettings, VarProjectResourceNames
from .pipeline_assembly import GenericPipeline
from .task_utils import apply_task_settings, with_gpu
from .workspace import GCPProject

PROJECT_NAME = "ML-ORCHESTRATOR"
__version__ = "0.1.0"
PROJECT_NAME = "ML-ORCHESTRATOR"
__version__ = "0.1.0"
PROJECT_VERSION = __version__

LOG_DATE = datetime.now().strftime("%Y-%m-%d")
LOG_PREFIX = f"{PROJECT_NAME}_{LOG_DATE}"
LOG_PATH = Path("logs")

logger.project_name = PROJECT_NAME
logger.file_directory = str(LOG_PATH)
logger.file_prefix = LOG_PREFIX

__all__ = [
    "GCPProject",
    "GenericPipeline",
    "PipelineConfig",
    "TaskSettings",
    "apply_task_settings",
    "with_gpu",
    "Env",
    "VarProjectResourceNames",
    "get_pipeline_commands_and_arguments",
    "run_pipeline_command",
]
