"""Local web app: serves the converter UI and the /api/jobs backend, then opens
the browser. This is what the desktop launch (double-click the app) runs."""

from __future__ import annotations

import contextlib
import os
import socket
import threading
import webbrowser

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from nam_a2a1.api import router as api_router
from nam_a2a1.engine import resource_path

STATIC_DIR = resource_path("nam_a2a1/static")

app = FastAPI(title="NAM A2→A1 Converter")
app.include_router(api_router)


@app.get("/", response_class=FileResponse)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@contextlib.contextmanager
def _unbundled_env():
    """Temporarily undo PyInstaller's LD_LIBRARY_PATH injection.

    The Linux bootloader prepends the bundle dir to LD_LIBRARY_PATH (stashing the
    original in LD_LIBRARY_PATH_ORIG) and every child inherits it. That is what the
    render/train workers want — they ARE the frozen exe — but a child that is NOT this
    app resolves its DT_NEEDED against our bundled libstdc++/libfreetype/libssl first.
    So xdg-open and the browser it launches can die with e.g. "version GLIBCXX_3.4.32
    not found", and the user just sees a browser that never opened. macOS is immune
    (SIP strips DYLD_* across spawn) and Windows has no equivalent; this is Linux-only,
    but the restore is a no-op elsewhere so it needs no platform guard.
    """
    saved = os.environ.get("LD_LIBRARY_PATH")
    orig = os.environ.get("LD_LIBRARY_PATH_ORIG")
    if orig is not None:
        os.environ["LD_LIBRARY_PATH"] = orig
    else:
        os.environ.pop("LD_LIBRARY_PATH", None)
    try:
        yield
    finally:
        if saved is None:
            os.environ.pop("LD_LIBRARY_PATH", None)
        else:
            os.environ["LD_LIBRARY_PATH"] = saved


def _open_browser(url: str) -> None:
    try:
        with _unbundled_env():
            opened = webbrowser.open(url)
    except Exception:  # noqa: BLE001 - a failed browser launch must not kill the server
        opened = False
    if not opened:
        print(f"Could not open a browser automatically. Open this URL manually: {url}")


def serve(
    host: str = "127.0.0.1", port: int | None = None, open_browser: bool = True
) -> None:
    import uvicorn

    if port is None:
        port = _free_port()
    url = f"http://{host}:{port}/"
    if open_browser:
        threading.Timer(1.0, lambda: _open_browser(url)).start()
    # __main__._ensure_std_streams guarantees sys.stdout exists (devnull in a windowed
    # build with no console), so this needs no None guard. Kept ASCII so it can't fail on
    # a non-UTF-8 console.
    print(f"NAM A2->A1 Converter running at {url}  (Ctrl+C to quit)")
    uvicorn.run(app, host=host, port=port, log_level="warning")
