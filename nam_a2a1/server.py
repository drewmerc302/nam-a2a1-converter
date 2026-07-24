"""Local web app: serves the converter UI and the /api/jobs backend, then opens
the browser. This is what the desktop launch (double-click the app) runs."""

from __future__ import annotations

import socket
import sys
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


def serve(
    host: str = "127.0.0.1", port: int | None = None, open_browser: bool = True
) -> None:
    import uvicorn

    if port is None:
        port = _free_port()
    url = f"http://{host}:{port}/"
    if open_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    # In a windowed (console=False) frozen build sys.stdout is None; guard the print
    # and keep it ASCII so it can't crash launch on a non-UTF-8 console.
    if sys.stdout is not None:
        print(f"NAM A2->A1 Converter running at {url}  (Ctrl+C to quit)")
    uvicorn.run(app, host=host, port=port, log_level="warning")
