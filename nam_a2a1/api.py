"""Batch conversion job API. POST /api/jobs launches a background conversion and
returns a job_id; GET endpoints poll the in-memory job store. Conversions take
minutes and shell out to subprocesses, so they run off the request thread."""

from __future__ import annotations

import threading
import uuid
from pathlib import Path
from typing import Callable, Dict, List

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from nam_a2a1 import __version__, accel, engine
from nam_a2a1.engine import ConvertJob, FileState

router = APIRouter(prefix="/api")


@router.get("/version")
def get_version() -> dict:
    """Which build this is. Kept separate from /api/accel on purpose: that one shells
    out to a worker that imports torch and takes seconds to answer, and a version
    string is only useful if it is on screen when someone is trying to tell you what
    they are running. Nothing here touches torch, so it returns instantly."""
    return {"version": __version__}


@router.get("/accel")
def get_accel() -> dict:
    """What the converter will train on, and whether a faster build exists for this
    machine. Deliberately a plain `def`: accel.status() shells out to a worker that
    imports torch, so FastAPI runs it in the threadpool instead of stalling the event
    loop for the few seconds that takes. Cached after the first call."""
    return accel.status()


WORK_DIR = Path.home() / "NAM-A2A1-out" / ".jobs"

_jobs: Dict[str, ConvertJob] = {}
_jobs_lock = threading.Lock()


def _run_and_isolate(job: ConvertJob) -> None:
    try:
        engine.run_job(job, lambda state: None)
    except Exception as e:
        for state in job.files:
            if state.status not in ("done", "failed", "cancelled"):
                state.status = "failed"
                state.error = f"job failed: {e}"


def _background_executor(job: ConvertJob) -> None:
    threading.Thread(target=_run_and_isolate, args=(job,), daemon=True).start()


# Swappable so tests can run synchronously.
job_executor: Callable[[ConvertJob], None] = _background_executor


def _get_job_or_404(job_id: str) -> ConvertJob:
    with _jobs_lock:
        job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(404, f"no such job {job_id!r}")
    return job


@router.post("/jobs")
async def create_job(
    files: List[UploadFile] = File(...),
    epochs: int = Form(60),
    output_format: str = Form("0.5x"),
) -> dict:
    if not files:
        raise HTTPException(400, "no files uploaded")
    for f in files:
        if not (f.filename or "").lower().endswith(".nam"):
            raise HTTPException(400, f"not a .nam file: {f.filename!r}")

    job_id = uuid.uuid4().hex
    in_dir = WORK_DIR / job_id / "in"
    out_dir = WORK_DIR / job_id / "out"
    in_dir.mkdir(parents=True, exist_ok=True)

    input_paths = []
    for f in files:
        dest = in_dir / Path(f.filename).name
        dest.write_bytes(await f.read())
        input_paths.append(dest)

    job = ConvertJob(
        input_paths=input_paths,
        epochs=epochs,
        output_format=output_format,
        out_dir=out_dir,
    )
    with _jobs_lock:
        _jobs[job_id] = job
    job_executor(job)
    return {
        "job_id": job_id,
        "files": [{"name": s.name, "status": s.status} for s in job.files],
    }


@router.get("/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    job = _get_job_or_404(job_id)
    return {
        "job_id": job_id,
        "output_format": job.output_format,
        "epochs": job.epochs,
        "files": [
            {
                "name": s.name,
                "status": s.status,
                "progress": s.progress,
                "detail": s.detail,
                "eta_seconds": s.eta_seconds,
                "esr": s.esr,
                "format_ok": s.format_ok,
                "error": s.error,
                "src_arch": s.src_arch,
                "output_available": bool(s.output_path)
                and Path(s.output_path).exists(),
            }
            for s in job.files
        ],
    }


@router.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: str) -> dict:
    job = _get_job_or_404(job_id)
    job.request_cancel()
    return {"job_id": job_id, "cancelled": True}


@router.get("/jobs/{job_id}/download/{name}")
def download(job_id: str, name: str) -> FileResponse:
    job = _get_job_or_404(job_id)
    safe = Path(name).name
    if safe.endswith(".nam"):
        safe = safe[: -len(".nam")]
    state = next((s for s in job.files if s.name == safe), None)
    if state is None or state.status != "done" or not state.output_path:
        raise HTTPException(404, f"output not available for {name!r}")
    out_path = Path(state.output_path)
    if not out_path.exists():
        raise HTTPException(404, f"output file missing for {name!r}")
    return FileResponse(
        out_path, filename=f"{safe}.nam", media_type="application/octet-stream"
    )
