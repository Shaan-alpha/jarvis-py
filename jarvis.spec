# jarvis.spec  — PyInstaller one-folder build
# Build with:  pyinstaller jarvis.spec
# Output:      dist/JarvisAI/  (Jarvis.exe + _internal/ + models/ + hud/)

block_cipher = None

a = Analysis(
    ["app.py"],
    pathex=["."],
    binaries=[],
    datas=[
        ("models", "models"),
        ("hud/web", "hud/web"),
    ],
    hiddenimports=[
        "webview",
        "vosk",
        "openwakeword",
        "faiss",
        "fastembed",
    ],
    excludes=[
        "tkinter",
        "matplotlib",
        "PyQt5",
        "PySide6",
    ],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Jarvis",
    console=True,        # keep a console for logs during early adoption
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    name="JarvisAI",
)
