# jarvis.spec  — PyInstaller one-folder build
# Build with:  pyinstaller jarvis.spec
# Output:      dist/JarvisAI/  (Jarvis.exe + _internal/<bundled assets>)

from PyInstaller.utils.hooks import collect_all

block_cipher = None

# Our own bundled assets (resolved at runtime via core.paths.resource_dir(),
# which points at _internal/ when frozen — PyInstaller >= 6 puts datas there).
datas = [
    ("models", "models"),
    ("hud/web", "hud/web"),
]

binaries = []

hiddenimports = ["webview"]

# vosk/openwakeword/faiss/fastembed ship native DLLs and/or bundled model data
# that a bare hiddenimport does NOT collect. vosk in particular loads
# libvosk.dll at import via add_dll_directory(dirname(__file__)), so the DLL
# must land in _internal/vosk/. collect_all() gathers data + binaries +
# submodules for each.
for _pkg in ("vosk", "openwakeword", "faiss", "fastembed"):
    _d, _b, _h = collect_all(_pkg)
    datas += _d
    binaries += _b
    hiddenimports += _h

a = Analysis(
    ["app.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
