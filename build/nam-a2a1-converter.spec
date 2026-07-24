# PyInstaller spec — freezes the converter (web UI + engine + torch pipeline) into
# a onedir app. Entry is run.py, which self-dispatches serve/render/train, so the
# frozen exe acts as both the app and its own render/train worker.
#
# Build from the repo root:  pyinstaller build/nam-a2a1-converter.spec
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = [], [], []
for pkg in ("nam", "torch", "pytorch_lightning", "torchmetrics", "soundfile", "numpy"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

# Lazy imports inside __main__.main() PyInstaller can't see statically.
hiddenimports += [
    "nam_a2a1",
    "nam_a2a1.__main__",
    "nam_a2a1.server",
    "nam_a2a1.api",
    "nam_a2a1.engine",
    "nam_a2a1.pipeline",
    "nam_a2a1.pipeline.render_a2",
    "nam_a2a1.pipeline.train_a1_070",
    "nam_a2a1.pipeline.distill_protocol",
    "nam_a2a1.pipeline.nam_transcode",
    "nam_a2a1.pipeline.make_di",
    "uvicorn",
    "uvicorn.logging",
    "uvicorn.loops.auto",
    "uvicorn.protocols.http.auto",
    "uvicorn.lifespan.on",
    "fastapi",
    "multipart",
]

# Runtime data: the standard DI and the web UI.
datas += [
    ("../refs/v3_0_0.wav", "refs"),
    ("../nam_a2a1/static", "nam_a2a1/static"),
]

a = Analysis(
    ["../run.py"],
    pathex=[".."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "PyQt5", "PySide2"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="nam-a2a1-converter",
    console=False,   # windowed app; workers still stream via captured pipes
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="nam-a2a1-converter",
)
