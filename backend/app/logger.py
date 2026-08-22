from loguru import logger
import sys
from .settings import settings

log_level = settings.LOG_LEVEL.upper()
logger.remove()
logger.add(
    sys.stdout,
    level=log_level,
    serialize=True,
    backtrace=True,
    diagnose=True,
)
