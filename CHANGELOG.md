## v2.4.0
- Removed dead Keras intent-classifier pipeline (chat_model.h5, train.py,
  tokenizer, label_encoder, model_test)
- Removed orphan `core/memory/memory.json` seed file and outdated
  `docs/README.md`
- Dropped scikit-learn dep — semantic-memory cosine is now numpy
- Vosk now loads from local `models/vosk/...` (auto-download fallback)
- Connectivity check constants moved into settings
  (ONLINE_CHECK_HOST/PORT/TIMEOUT, ONLINE_CACHE_TTL)
- Routing reordered: keyword router (fast) → LLM tool agent (slow) →
  LLM chat fallback. Previously every query hit the LLM tool agent
  first even for trivial commands.
- Vosk model pre-warmed in a background thread at app startup so the
  first offline transcription does not pay the model-load cost
- Reminders rewritten with threading.Timer (one-shot, second-accurate);
  dropped the `schedule` lib and its minute-rounding restore bug
- requirements.txt trimmed and grouped; requirements-dev.txt slimmed
- Stale requirements-lock.txt removed
- .gitignore now excludes runtime caches (vector.index, chunks.pkl,
  semantic_memory.json, tasks.json)
- README updated to reflect dual STT + lean stack

## v2.3.0
- Hybrid online/offline STT with auto-fallback (Google ↔ Vosk)
- New connectivity check `is_online()` in speech/engine
- Fixed browser handler to URL-encode and open a real Google search

## v2.2.0
- Real wake-word detection via openWakeWord (`hey_jarvis`)
- Replaces the broken stub that loaded every bundled pretrained model
- WAKE_THRESHOLD pulled from settings; clean PyAudio teardown

## v2.1.0
- Removed duplicate `User said` / `Jarvis:` console prints
- Centralized embedder, cached document index + memory embeddings
- Unified tool agent/executor schema via `tool_registry` (executor was
  importing a non-existent `core.actions.system_actions` module)
- Greeting reads name from user profile
- Populated `data/profile/user_profile.json`
