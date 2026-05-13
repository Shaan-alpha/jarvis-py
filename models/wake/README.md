# models/wake/

Wake-word detection ONNX. By default Jarvis listens for **"hey jarvis"**.

## How resolution works

`core/speech/openwakeword_listener.py` searches in this order:

1. **Local override** at `models/wake/hey_jarvis_v0.1.onnx`
   (matches `WAKE_MODEL_PATH` in `config/settings.py`).
2. The bundled file inside the installed `openwakeword` Python package
   (`<site-packages>/openwakeword/resources/models/`).
3. Auto-download via `openwakeword.utils.download_models(['hey_jarvis'])`
   into the package directory.

So you don't need to do anything — the first run will download it. If
you want project-local control (e.g. for offline installs or PyInstaller
bundling), copy the ONNX here.

## Using a different wake word

Edit `WAKE_WORD` and `WAKE_MODEL_PATH` in `config/settings.py`. Other
bundled options: `alexa`, `hey_mycroft`, `hey_rhasspy`. Or train your
own with [openwakeword's training pipeline](https://github.com/dscripka/openWakeWord).
