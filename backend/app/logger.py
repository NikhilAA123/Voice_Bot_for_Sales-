import sys

from loguru import logger

from .settings import settings

# Windows consoles default to legacy codepages; force UTF-8 so JSON logs
# never crash on non-ASCII characters (curly quotes, emojis, Hindi/Telugu).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

log_level = settings.LOG_LEVEL.upper()
logger.remove()
logger.add(
    sys.stdout,
    level=log_level,
    serialize=True,
    backtrace=True,
    diagnose=True,
)
