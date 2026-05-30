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


logging.basicConfig(
    level=logging.INFO,

    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(message)s"
    ),

    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)


logger = logging.getLogger(
    "Jarvis"
)
