import os

from core.paths import resource_dir

MODEL_NAME = "phi3"

OLLAMA_URL = "http://localhost:11434/api/generate"

# Ollama model-list endpoint (used by setup checks)
OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"

WAKE_THRESHOLD = 0.4

SESSION_TIMEOUT = 20

VOICE_RATE = -25

VOICE_VOLUME = 1.0

MEMORY_SIMILARITY_THRESHOLD = 0.45

DOCUMENT_SIMILARITY_THRESHOLD = 0.45

VOSK_MODEL_PATH = os.path.join(
    str(resource_dir()),
    "models",
    "vosk",
    "vosk-model-small-en-us-0.15"
)

WAKE_WORD = "hey_jarvis"

WAKE_MODEL_PATH = os.path.join(
    str(resource_dir()),
    "models",
    "wake",
    "hey_jarvis_v0.1.onnx"
)

ONLINE_CHECK_HOST = "8.8.8.8"

ONLINE_CHECK_PORT = 53

ONLINE_CHECK_TIMEOUT = 1.0

ONLINE_CACHE_TTL = 5.0

# -------------------- #
# HUD (desktop overlay)
# -------------------- #

HUD_WS_HOST = "127.0.0.1"

HUD_WS_PORT = 8765

HUD_STATS_INTERVAL = 3.0

# Theme schedule (24h). Day -> cyan, evening -> gold, night -> frost.
HUD_THEME_DAY_START = 5

HUD_THEME_EVENING_START = 17

HUD_THEME_NIGHT_START = 21
