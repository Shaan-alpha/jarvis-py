# JARVIS-PY

![Python](https://img.shields.io/badge/Python-3.13-blue)
![Ollama](https://img.shields.io/badge/LLM-Ollama-black)
![Status](https://img.shields.io/badge/status-active-success)
![License](https://img.shields.io/badge/license-MIT-green)

> Local-first AI voice assistant with online/offline speech recognition, wake-word detection, semantic memory, document RAG, streaming LLM responses, a tool-agent, and interruptible TTS.

## Overview

JARVIS-PY is a Python voice assistant built for:

- Local-first, offline-capable operation
- Real-time voice interaction with **wake-word barge-in** (interrupt mid-reply)
- Semantic conversation memory + PDF document RAG
- AI-driven tool routing
- Fast keyword routing for known intents
- Modular, easy-to-package architecture

---

## Core Features

### Speech
- **Wake word**: openWakeWord `hey_jarvis` (ONNX, ~1 MB)
- **STT online**: Google (`speech_recognition.recognize_google`)
- **STT offline**: Vosk (local model, auto-fallback when offline)
- **TTS**: pyttsx3 (SAPI5 / NSSpeechSynthesizer / espeak)
- **Streaming sentence-level TTS queue** — each sentence speaks fully before the next, no cut-offs
- **Barge-in** — say "hey jarvis" again while Jarvis is talking to interrupt and issue a new command

### Brain
- Local LLM via Ollama (default `phi3`)
- Streaming token output
- Semantic memory retrieval (fastembed ONNX + numpy cosine)
- Document RAG over PDFs (FAISS, similarity-thresholded — your résumé won't leak into unrelated answers)
- User profile context injected into every prompt

### Routing
- Fast keyword router for app / media / browser / system intents
- LLM tool agent fallback for fuzzy matches (action-verb gated to skip unnecessary LLM hops)
- LLM chat as final fallback

### Tasks
- Voice-set reminders (*"remind me in 10 minutes to ..."*)
- Persisted across restarts, fired by `threading.Timer` (second-accurate)

---

## Architecture

```text
USER SPEAKS
    ↓
Wake-word Detection (openWakeWord)
    ↓
STT  ─── online?  ─── Google ──┐
       └─ offline ─── Vosk  ───┤
                               ▼
               clean_query → routing
                               │
        ┌─── reminders / exit / profile capture
        ├─── fast keyword router (intents)
        ├─── action-verb gate → LLM tool agent
        └─── LLM chat fallback (Ollama)
                               ↓
                Streaming TTS queue (serialized)
                               ↓
                       pyttsx3 speak
                               ↑
            barge-in listener  │  ← "hey jarvis"
                  interrupts ──┘
```

Detailed: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## Tech Stack

| Layer | Tech |
|---|---|
| LLM | Ollama (Phi3 default) |
| Embeddings | fastembed (ONNX, no torch / transformers) |
| Vector index | FAISS (cosine via IndexFlatIP) |
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
├── debug_wake.py           # diagnose wake-word + mic
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
├── data/                   # runtime data (gitignored, READMEs in each folder)
│   ├── documents/          # drop PDFs here
│   ├── profile/            # user_profile.json
│   └── tasks/              # reminders persistence
└── models/                 # ML models (gitignored, READMEs in each folder)
    ├── wake/               # openWakeWord ONNX
    ├── vosk/               # Vosk STT model
    └── embeddings/         # fastembed cache
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

Install from <https://ollama.com/>, then:

```bash
ollama pull phi3
```

### Vosk model (offline STT)

The auto-download path works out of the box (Vosk fetches to `~/.cache/vosk/` on first offline use). For a project-local install, see [models/vosk/README.md](models/vosk/README.md).

### Wake-word model

Auto-downloaded into the openWakeWord package on first run (one-time, ~1 MB). For a project-local override, see [models/wake/README.md](models/wake/README.md).

### User profile

Optional — see [data/profile/README.md](data/profile/README.md) to pre-populate `user_profile.json` so Jarvis greets you by name.

### Documents (PDF RAG)

Optional — drop PDFs in `data/documents/` and run `python build_memory.py`. See [data/documents/README.md](data/documents/README.md).

---

## Run

```bash
python app.py
```

Speak the wake phrase **"hey jarvis"**, wait for *"Yes Boss?"*, then issue your command.

**Barge-in:** if Jarvis is talking and you want to cut them off, say *"hey jarvis"* again. The current sentence is cancelled and Jarvis listens for your next command immediately.

**Exit / sleep:** say *"bye"*, *"goodbye"*, *"exit"*, *"shutdown"*, or *"stop listening"*. Or wait 20 s in silence.

**Diagnostics:** if the wake word never fires, run `python debug_wake.py` — it lists your input devices and prints live wake-word confidence scores.

---

## Config

All config in [config/settings.py](config/settings.py):

| Key | Default | Purpose |
|---|---|---|
| `MODEL_NAME` | `phi3` | Ollama model |
| `WAKE_WORD` | `hey_jarvis` | openWakeWord model name |
| `WAKE_MODEL_PATH` | `models/wake/hey_jarvis_v0.1.onnx` | Project-local wake-word ONNX override |
| `WAKE_THRESHOLD` | `0.4` | Wake-word confidence cutoff |
| `SESSION_TIMEOUT` | `20` | Seconds of silence before returning to sleep |
| `VOSK_MODEL_PATH` | `models/vosk/vosk-model-small-en-us-0.15` | Project-local Vosk model |
| `MEMORY_SIMILARITY_THRESHOLD` | `0.45` | Min cosine for conversation-memory recall |
| `DOCUMENT_SIMILARITY_THRESHOLD` | `0.45` | Min cosine for doc-RAG injection |
| `ONLINE_CHECK_*` | `8.8.8.8:53`, 1 s timeout, 5 s cache | Online/offline auto-detection |

---

## License

MIT
