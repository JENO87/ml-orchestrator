"""Package for Development Template.

Contains variable PROJECT_NAME and VERSION
"""

from datetime import datetime
from pathlib import Path

PROJECT_NAME = "DEV-TEMPLATE"
__version__ = "0.1.0"
PROJECT_VERSION = __version__

LOG_DATE = datetime.now().strftime("%Y-%m-%d")
LOG_PREFIX = f"{PROJECT_NAME}_{LOG_DATE}"
LOG_PATH = Path("logs")
