# JARVIS-PY

> Local-first AI voice assistant with online/offline speech recognition, wake-word detection, semantic memory, document RAG, streaming LLM responses, and a tool-agent.

## Overview

JARVIS-PY is a Python voice assistant built for:

- Local-first, offline-capable operation
- Real-time voice interaction with interruptible TTS
- Semantic conversation memory + PDF document RAG
- AI-driven tool routing
- Fast keyword routing for known intents
- Modular, easy-to-package architecture

---

## Core Features

### Speech
- **Wake word**: openWakeWord (`hey_jarvis`)
- **STT online**: Google (`speech_recognition.recognize_google`)
- **STT offline**: Vosk (local model, auto-fallback when offline)
- **TTS**: pyttsx3 (SAPI5 / NSSpeechSynthesizer / espeak)
- Streaming sentence-level TTS queue for low-latency replies

### Brain
- Local LLM via Ollama (default `phi3`)
- Streaming token output
- Semantic memory retrieval (sentence-transformers + numpy cosine)
- Document RAG over PDFs (FAISS index)
- User profile context injected into every prompt

### Routing
- Fast keyword router for app/media/browser/system intents
- LLM tool agent fallback for fuzzy matches
- LLM chat as final fallback

### Tasks
- Voice-set reminders ("remind me in 10 minutes to ...")
- Persisted across restarts, fired by `threading.Timer`

---

## Architecture

```text
USER SPEAKS
    ↓
Wake-word Detection (openWakeWord)
    ↓
STT  ─── online? ─── Google ──┐
       └── offline ── Vosk ───┤
                              ▼
              clean_query → router
                              │
        ┌─── reminders / exit / profile capture
        ├─── fast keyword router (intents)
        ├─── LLM tool agent (slow path)
        └─── LLM chat fallback (Ollama)
                              ↓
                     Streaming TTS queue
                              ↓
                       pyttsx3 speak
```

Detailed: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## Tech Stack

| Layer | Tech |
|---|---|
| LLM | Ollama (Phi3 default) |
| Embeddings | sentence-transformers |
| Vector index | FAISS |
| STT online | SpeechRecognition + Google |
| STT offline | Vosk (small-en-us) |
| Wake word | openWakeWord (ONNX) |
| TTS | pyttsx3 |
| System control | PyAutoGUI, psutil |

---

## Project Layout

```text
jarvis-py/
├── app.py                  # main loop
├── build_memory.py         # rebuild PDF vector index
├── config/settings.py
├── core/
│   ├── ai/                 # ollama LLM client
│   ├── agent/              # tool agent + registry + executor
│   ├── speech/             # wake, engine, online/offline STT, TTS queue
│   ├── memory/             # embedder, semantic, document, profile
│   ├── router/             # fast keyword intent router
│   ├── intents/            # intent handlers
│   ├── tasks/              # reminders + persistence
│   ├── state/              # session
│   ├── commands/           # browser/social/schedule helpers
│   ├── automation/         # OS app open/close, sys status
│   └── utils/              # logger, greetings
├── data/                   # documents, profile, tasks (runtime)
└── models/                 # vosk model (not committed)
```

---

## Installation

```bash
git clone https://github.com/Shaan-alpha/jarvis-py.git
cd jarvis-py
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

### Ollama

Install: <https://ollama.com/>

```bash
ollama pull phi3
```

### Vosk model (offline STT)

Download `vosk-model-small-en-us-0.15` from <https://alphacephei.com/vosk/models> and unzip into `models/vosk/vosk-model-small-en-us-0.15`. If missing, the assistant auto-downloads to `~/.cache/vosk/` on first offline use.

### Wake-word model

Auto-downloaded on first run (one-time, ~1 MB) into the openWakeWord package directory.

---

## Run

```bash
python app.py
```

Speak the wake phrase ("hey jarvis"), wait for "Yes Boss?", then issue your command.

Index your documents (optional):

```bash
# drop PDFs into data/documents/
python build_memory.py
```

---

## Config

All config in [config/settings.py](config/settings.py):

| Key | Default | Purpose |
|---|---|---|
| `MODEL_NAME` | `phi3` | Ollama model |
| `WAKE_THRESHOLD` | `0.5` | Wake-word confidence cutoff |
| `SESSION_TIMEOUT` | `20` | Seconds of silence → back to wake mode |
| `MEMORY_SIMILARITY_THRESHOLD` | `0.45` | Min cosine for memory recall |
| `VOSK_MODEL_PATH` | `models/vosk/...` | Local Vosk model directory |

---

## License

MIT
