# models/

All ML models live here. **Nothing in this folder is committed** —
each subfolder has a README explaining what to put in it and where to
download it from.

| Folder | Purpose | First-run behaviour |
|---|---|---|
| `wake/` | openWakeWord ONNX (~1 MB) | auto-downloaded into the openWakeWord package on first call; copy here for project-local override |
| `vosk/` | Vosk offline STT model (~50 MB) | auto-downloaded to `~/.cache/vosk/` if missing here |
| `embeddings/` | fastembed ONNX (~90 MB) | auto-downloaded on first embed call |
