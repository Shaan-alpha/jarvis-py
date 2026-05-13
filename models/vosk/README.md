# models/vosk/

Offline speech-to-text engine. Used when `is_online()` returns False
or when Google STT errors out.

## Manual install (recommended — keeps everything project-local)

1. Download `vosk-model-small-en-us-0.15.zip` (~40 MB) from
   <https://alphacephei.com/vosk/models>.
2. Unzip it here, so the path looks like:
   `models/vosk/vosk-model-small-en-us-0.15/`.
3. That matches `VOSK_MODEL_PATH` in `config/settings.py`.

## Auto-download fallback

If the path above is missing, `core/speech/offline_recognizer.py`
calls `vosk.Model(lang="en-us")` which auto-downloads the small
English model to `~/.cache/vosk/`. Slower first-offline command but
works without any setup.

## Other models

For a different language or a larger model, edit `VOSK_MODEL_PATH`
in `config/settings.py` to point at the unzipped folder.
