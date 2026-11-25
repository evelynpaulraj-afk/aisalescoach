# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the Sales Coach desktop app (one-folder build).
#   pyinstaller SalesCoach.spec --noconfirm --clean
# build_app.ps1 runs this for you after building the UI and fetching the models.

import os

from PyInstaller.utils.hooks import collect_all, collect_submodules

datas, binaries, hiddenimports = [], [], []

# Packages that ship data files, native libraries or lazily-imported modules
# that PyInstaller's static analysis misses. Anything not installed is skipped,
# so the spec still works if a package is absent.
PACKAGES_TO_COLLECT = [
    "faster_whisper",   # bundled VAD model
    "ctranslate2",      # Whisper runtime (native libraries)
    "onnxruntime",
    "tokenizers",
    "av",               # PyAV: audio decoding (ships its own ffmpeg libraries)
    "soundfile",
    "huggingface_hub",
    "pyannote.audio",
    "pyannote.core",
    "pyannote.database",
    "pyannote.metrics",
    "pyannote.pipeline",
    "lightning",
    "lightning_fabric",
    "pytorch_lightning",
    "torchmetrics",
    "lightning_utilities",
    "speechbrain",
    "asteroid_filterbanks",
    "torch_audiomentations",
    "julius",
    "omegaconf",
    "opentelemetry",
    "google.genai",
    "certifi",
]
for package in PACKAGES_TO_COLLECT:
    try:
        d, b, h = collect_all(package)
    except Exception as exc:  # not installed / nothing to collect
        print(f"[spec] skipping {package}: {exc}")
        continue
    datas += d
    binaries += b
    hiddenimports += h

# uvicorn picks its event loop / HTTP implementation at run time.
hiddenimports += collect_submodules("uvicorn")

# The built web UI (copied here by build_app.ps1) and the speech models.
if not os.path.isdir("ui"):
    raise SystemExit("The 'ui' folder is missing. Run build_app.ps1, which builds it first.")
datas.append(("ui", "ui"))
if os.path.isdir("models"):
    datas.append(("models", "models"))
else:
    print("[spec] WARNING: no 'models' folder - the app will need a Hugging Face token at run time.")

a = Analysis(
    ["launcher.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SalesCoach",
    debug=False,
    strip=False,
    upx=False,
    console=True,  # keep the console: it shows progress and closing it stops the app
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="SalesCoach",
)
