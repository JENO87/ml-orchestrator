"""Package for Machine Learning Orchestrator. Contains variable PROJECT_NAME."""

from datetime import datetime
from pathlib import Path

from loguru import logger

PROJECT_NAME = "ML-ORCHESTRATOR"
__version__ = "0.1.0"
PROJECT_VERSION = __version__

LOG_DATE = datetime.now().strftime("%Y-%m-%d")
LOG_PREFIX = f"{PROJECT_NAME}_{LOG_DATE}"
LOG_PATH = Path("logs")

logger.project_name = PROJECT_NAME
logger.file_directory = str(LOG_PATH)
logger.file_prefix = LOG_PREFIX