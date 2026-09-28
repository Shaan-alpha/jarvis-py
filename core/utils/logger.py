import logging
import os

from logging.handlers import RotatingFileHandler

from core.paths import user_data_dir


LOG_DIR = os.path.join(
    str(user_data_dir()),
    "logs"
)

LOG_FILE = os.path.join(
    LOG_DIR,
    "jarvis.log"
)


os.makedirs(
    LOG_DIR,
    exist_ok=True
)


# Rotate at 2 MB, keep 3 backups: the log records every query and had grown to
# 28 MB. Explicit utf-8: a Windows FileHandler otherwise encodes with the locale
# codepage (cp1252) and drops any line carrying a character outside it.
LOG_MAX_BYTES = 2 * 1024 * 1024

LOG_BACKUPS = 3

_file_handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=LOG_MAX_BYTES,
    backupCount=LOG_BACKUPS,
    encoding="utf-8"
)


logging.basicConfig(
    level=logging.INFO,

    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(message)s"
    ),

    handlers=[
        _file_handler,
        logging.StreamHandler()
    ]
)


logger = logging.getLogger(
    "Jarvis"
)
