import os

from core.paths import resource_dir

MODEL_NAME = "phi3"

OLLAMA_URL = "http://localhost:11434/api/generate"

# Ollama model-list endpoint (used by setup checks)
OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"

# Wake-word sensitivity. 0.6 suited the old (degraded MME) capture path. With
# clean WASAPI capture + resampling (see openwakeword_listener), ambient sits
# near 0, but real "hey jarvis" utterances vary a lot by distance/articulation:
# measured peaks ranged 0.47 (quiet) to 0.97 (clear). On some voices/mics a quiet
# pass peaks ~0.5 but only crosses the bar for a SINGLE frame, so a 2-consecutive
# requirement silently dropped ~4 of 5 attempts (the "it can't hear me" bug). With
# ambient staying well under 0.3, a single frame over threshold is a safe trigger,
# so WAKE_CONSECUTIVE is 1. Raise it to 2 if you get false wakes; lower THRESHOLD
# if it still misses you.
WAKE_THRESHOLD = 0.3

WAKE_CONSECUTIVE = 1

SESSION_TIMEOUT = 20

VOICE_RATE = -25

VOICE_VOLUME = 1.0

# Speech capture (speech_recognition). adjust_for_ambient_noise can push the
# energy threshold very high in a noisy room (or right after TTS), forcing the
# user to almost shout. Cap it here so normal-volume speech is still picked up;
# dynamic_energy_threshold still adapts from this ceiling. Lower if Jarvis
# ignores you; raise if it triggers on background noise. (sr default is 300.)
MAX_ENERGY_THRESHOLD = 400

MEMORY_SIMILARITY_THRESHOLD = 0.55

# Raised from 0.45: a weak match (e.g. a resume chunk scoring ~0.45 against a
# vague query like "how are you") was being injected into the prompt and the
# small model would confabulate around it. 0.6 keeps genuine document Q&A while
# rejecting tangential matches.
DOCUMENT_SIMILARITY_THRESHOLD = 0.6

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

# Chosen at startup by mic auto-detect; None = PyAudio default.
# INPUT_DEVICE_INDEX feeds STT (speech_recognition): prefers an MME/DirectSound
# mic, which downmixes to mono cleanly and which Google STT transcribes well.
# WAKE_DEVICE_INDEX feeds the wake-word listener: prefers the same mic on WASAPI,
# whose clean shared-mode audio openWakeWord needs (MME's "communications"
# processing scores ~0). They are the same physical mic via different host APIs;
# both fall back to the PyAudio default when None.
INPUT_DEVICE_INDEX = None

WAKE_DEVICE_INDEX = None

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
