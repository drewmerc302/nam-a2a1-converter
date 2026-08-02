# PyInstaller spec — freezes the converter (web UI + engine + torch pipeline) into
# a onedir app. Entry is run.py, which self-dispatches serve/render/train, so the
# frozen exe acts as both the app and its own render/train worker.
#
# Build from the repo root:  pyinstaller build/nam-a2a1-converter.spec
#
# On macOS this ALSO emits dist/nam-a2a1-converter.app. That bundle is the shipping
# artifact, not a convenience: Gatekeeper refuses to approve a bare Mach-O executable
# no matter how well it is signed ("the code is valid but does not seem to be an app"),
# and a notarization ticket can only be stapled to a bundle, dmg or pkg — never to a
# loose binary. v0.4.2 and earlier shipped the loose COLLECT output inside the dmg, so
# every macOS user hit the malware warning on a correctly signed, notarized build.
import os
import re
import sys

from PyInstaller.utils.hooks import collect_all

_init = os.path.join(SPECPATH, "..", "nam_a2a1", "__init__.py")  # noqa: F821 (PyInstaller global)
with open(_init, encoding="utf-8") as _fp:
    VERSION = re.search(r'__version__\s*=\s*"([^"]+)"', _fp.read()).group(1)

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
    "nam_a2a1.pipeline.y_gain",
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
    # NB: neural-amp-modeler imports tkinter AND matplotlib at module load
    # (nam.train.core), and nam.models pulls nam.train transitively — so both must
    # be bundled even though this app never shows a GUI plot. matplotlib falls back
    # to the Agg backend, so the Qt bindings can stay excluded.
    excludes=["PyQt5", "PySide2"],
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

# macOS only. BUNDLE is a no-op elsewhere, but guard it anyway so the Windows and
# Linux legs never depend on that.
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="nam-a2a1-converter.app",
        icon=None,
        bundle_identifier="com.drewmerc.nam-a2a1-converter",
        version=VERSION,
        info_plist={
            "CFBundleName": "NAM A2A1 Converter",
            "CFBundleDisplayName": "NAM A2 to A1 Converter",
            "CFBundleShortVersionString": VERSION,
            "CFBundleVersion": VERSION,
            "NSHighResolutionCapable": True,
            # The app has no window of its own — it opens the converter page in the
            # user's browser — but it must NOT be LSUIElement: the Dock icon is the
            # only way to quit it.
            "LSMinimumSystemVersion": "12.0",
        },
    )
