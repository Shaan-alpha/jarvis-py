# JARVIS-PY

> Offline AI voice assistant with semantic memory, streaming responses, local LLM inference, wake-word detection, and modular tool-agent architecture.

## Overview

JARVIS-PY is a local-first AI assistant built in Python with a focus on:

- Fast local inference
- Offline-first architecture
- Modular engineering
- Real-time voice interaction
- Semantic memory retrieval
- AI-driven tool execution

Unlike traditional assistant tutorials, this project focuses heavily on scalable architecture, concurrency, streaming systems, and deployability.

---

## Core Features

### AI + Reasoning
- Local LLM inference using Ollama
- Streaming token responses
- Semantic memory retrieval
- Context-aware prompting
- AI tool-routing agent

### Voice System
- Wake-word detection
- Interruptible speech
- Streaming TTS queue
- Concurrent audio handling
- Real-time speech recognition

### Automation
- System automation
- Volume control
- Application launching
- Browser interaction
- Extensible tool execution layer

### Architecture
- Modular folder structure
- Session state management
- Centralized configuration system
- Local-first deployment design
- Threaded concurrency model

---

## Architecture

```text
USER SPEAKS
    ↓
Wake Word Detection
    ↓
Speech Recognition
    ↓
Tool Agent Decision
    ↓
Tool Execution OR LLM
    ↓
Semantic Memory Retrieval
    ↓
Streaming Response
    ↓
TTS Queue System
```

Detailed architecture:

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

---

## Tech Stack

| Layer | Technology |
|---|---|
| LLM | Ollama + Phi3 |
| Memory | SentenceTransformers |
| Similarity | Scikit-learn |
| Speech Recognition | SpeechRecognition |
| Wake Word | OpenWakeWord |
| TTS | pyttsx3 |
| Automation | PyAutoGUI |
| Runtime | Python |

---

## Project Structure

```text
jarvis-py/
│
├── core/
│   ├── ai/
│   ├── agent/
│   ├── speech/
│   ├── memory/
│   ├── router/
│   ├── state/
│   └── utils/
│
├── config/
├── docs/
├── logs/
├── tests/
└── models/
```

---

## Installation

### Clone Repository

```bash
git clone https://github.com/Shaan-alpha/jarvis-py.git
cd jarvis-py
```

### Create Virtual Environment

```bash
python -m venv venv
```

### Activate Environment

#### Windows

```bash
venv\Scripts\activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Install Ollama

Download:

https://ollama.com/

Run model:

```bash
ollama run phi3
```

---

## Run JARVIS

```bash
python app.py
```

---

## Current Status

### Stable Features
- Semantic memory
- Streaming LLM responses
- Streaming TTS queue
- AI tool routing
- Wake-word system
- Session management
- Interruptible speech
- Modular architecture

---

## Future Roadmap

- Piper TTS integration
- GUI overlay
- Event bus architecture
- Advanced agent workflows
- Better wake-word models
- Packaging with Nuitka
- Plugin system

---

## License

MIT License
