import logging
import os

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


# Explicit utf-8: a Windows FileHandler otherwise encodes with the locale
# codepage (cp1252 here), and any transcript or reply carrying a character
# outside it raises inside logging — the line is dropped and a traceback is
# printed in its place.
_file_handler = logging.FileHandler(
    LOG_FILE,
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
