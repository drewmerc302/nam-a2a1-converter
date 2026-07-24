"""Conversion engine: distill NAM A2 captures into A1 .nam files.

Runs the two-stage distill (render a DI through the A2, then train an A1 to match)
by shelling out to worker subprocesses. In a normal checkout the worker is
`python -m nam_a2a1 <render|train> ...`; in a PyInstaller-frozen app there is no
`python` to call, so the worker is the frozen executable re-invoking itself
(`sys.executable <render|train> ...`). Keeping the stages as subprocesses means a
cancel can SIGTERM the running one instead of waiting out a ~20-minute train.
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from nam_a2a1.pipeline import distill_protocol


def resource_path(rel: str) -> Path:
    """Resolve a bundled data file both in a source checkout and when frozen."""
    base = getattr(sys, "_MEIPASS", None)
    if base:  # PyInstaller onedir/onefile temp root
        return Path(base) / rel
    return Path(__file__).resolve().parent.parent / rel


DEFAULT_DI = resource_path("refs/v3_0_0.wav")
DEFAULT_OUT_DIR = Path.home() / "NAM-A2A1-out"


def _worker_base() -> List[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable]
    return [sys.executable, "-m", "nam_a2a1"]


@dataclass
class FileState:
    """Per-file conversion state, updated in place and read by the API/UI."""

    input_path: str
    name: str
    status: str = "queued"  # queued|detecting|rendering|training|done|failed|cancelled
    progress: float = 0.0
    esr: Optional[float] = None
    output_path: Optional[str] = None
    format_ok: Optional[bool] = None
    error: Optional[str] = None
    src_arch: Optional[str] = None
    detail: Optional[str] = None
    eta_seconds: Optional[float] = None


ProgressCallback = Callable[[FileState], None]


@dataclass
class ConvertJob:
    input_paths: List[Path]
    di_path: Path = DEFAULT_DI
    epochs: int = 60
    output_format: str = "0.5x"  # '0.5x' (A1-only devices, e.g. GP-50) | '0.7.0'
    out_dir: Path = DEFAULT_OUT_DIR
    files: List[FileState] = field(default_factory=list)
    _cancel_event: threading.Event = field(default_factory=threading.Event, repr=False)
    _proc_lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _current_proc: Optional[subprocess.Popen] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        self.input_paths = [Path(p) for p in self.input_paths]
        self.di_path = Path(self.di_path)
        self.out_dir = Path(self.out_dir)
        if not self.files:
            self.files = [
                FileState(input_path=str(p), name=p.stem) for p in self.input_paths
            ]

    @property
    def cancelled(self) -> bool:
        return self._cancel_event.is_set()

    def request_cancel(self) -> None:
        self._cancel_event.set()
        with self._proc_lock:
            proc = self._current_proc
        if proc is None or proc.poll() is not None:
            return
        try:
            if os.name == "nt":
                # No child procs (dataloader num_workers=0), so terminating the
                # worker is enough; Windows has no killpg.
                proc.terminate()
            else:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except (ProcessLookupError, PermissionError, OSError):
            pass


def detect_architecture(nam_path: Path) -> Tuple[Optional[str], str]:
    with open(nam_path) as fp:
        d = json.load(fp)
    return d.get("architecture"), str(d.get("version", "?"))


def _popen(cmd: List[str], job: ConvertJob) -> Optional[subprocess.Popen]:
    # POSIX: own session so a SIGTERM reaches the whole group. Windows: suppress
    # the console window each worker would otherwise flash in a windowed build.
    kwargs = {}
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    else:
        kwargs["start_new_session"] = True
    with job._proc_lock:
        if job._cancel_event.is_set():
            return None
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            **kwargs,
        )
        job._current_proc = proc
        return proc


def _run(cmd: List[str], job: ConvertJob) -> subprocess.CompletedProcess:
    proc = _popen(cmd, job)
    if proc is None:
        return subprocess.CompletedProcess(cmd, -1, "", "cancelled")
    try:
        out, _ = proc.communicate()
    finally:
        with job._proc_lock:
            job._current_proc = None
    return subprocess.CompletedProcess(cmd, proc.returncode, out, "")


def _run_streaming(
    cmd: List[str], job: ConvertJob, on_line
) -> subprocess.CompletedProcess:
    proc = _popen(cmd, job)
    if proc is None:
        return subprocess.CompletedProcess(cmd, -1, "", "cancelled")
    lines: List[str] = []
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            lines.append(line)
            try:
                on_line(line)
            except Exception:
                pass
        proc.wait()
    finally:
        with job._proc_lock:
            job._current_proc = None
    return subprocess.CompletedProcess(cmd, proc.returncode, "".join(lines), "")


def _update(state: FileState, progress_cb: ProgressCallback, **changes) -> None:
    for k, v in changes.items():
        setattr(state, k, v)
    progress_cb(state)


def _convert_one(
    state: FileState, job: ConvertJob, progress_cb: ProgressCallback
) -> None:
    src = Path(state.input_path)

    _update(state, progress_cb, status="detecting", progress=0.05)
    try:
        arch, version = detect_architecture(src)
    except Exception as e:
        _update(state, progress_cb, status="failed", error=f"could not read .nam: {e}")
        return
    state.src_arch = arch

    if arch == "WaveNet" and version.startswith("0.5"):
        job.out_dir.mkdir(parents=True, exist_ok=True)
        dest = job.out_dir / f"{state.name}.nam"
        try:
            shutil.copyfile(src, dest)
        except Exception as e:
            _update(state, progress_cb, status="failed", error=f"copy failed: {e}")
            return
        _update(
            state,
            progress_cb,
            status="done",
            progress=1.0,
            output_path=str(dest),
            format_ok=True,
            detail="already A1 (0.5.x) — copied",
        )
        return

    if arch != "SlimmableContainer":
        _update(
            state,
            progress_cb,
            status="failed",
            error=f"unsupported source architecture {arch!r} (version {version})",
        )
        return

    with tempfile.TemporaryDirectory(prefix=f"nam_{state.name}_") as workdir_s:
        workdir = Path(workdir_s)
        y_wav = workdir / "y.wav"

        _update(
            state,
            progress_cb,
            status="rendering",
            progress=0.2,
            detail="Rendering teacher signal (~1 min)…",
        )
        render = _run(
            _worker_base() + ["render", str(src), str(job.di_path), str(y_wav)], job
        )
        if job.cancelled:
            _update(state, progress_cb, status="cancelled", error="cancelled by user")
            return
        if render.returncode != 0 or not y_wav.exists():
            _update(
                state,
                progress_cb,
                status="failed",
                error=f"render failed (rc={render.returncode}): {render.stdout[-500:]}",
            )
            return

        _update(
            state,
            progress_cb,
            status="training",
            progress=0.5,
            detail=f"Training 0/{job.epochs}",
        )
        train_started = time.monotonic()

        def _on_train_line(line: str) -> None:
            prog = distill_protocol.parse_progress(line)
            if prog is None:
                return
            done, total = prog
            if total <= 0:
                return
            elapsed = time.monotonic() - train_started
            eta = (elapsed / done) * (total - done) if done > 0 else None
            _update(
                state,
                progress_cb,
                progress=0.5 + 0.45 * (done / total),
                detail=f"Training {done}/{total}",
                eta_seconds=eta,
            )

        train = _run_streaming(
            _worker_base()
            + [
                "train",
                str(job.di_path),
                str(y_wav),
                str(workdir),
                "--epochs",
                str(job.epochs),
                "--arch",
                "standard",
                "--format",
                job.output_format,
            ],
            job,
            _on_train_line,
        )
        if job.cancelled:
            _update(state, progress_cb, status="cancelled", error="cancelled by user")
            return
        if train.returncode != 0:
            _update(
                state,
                progress_cb,
                status="failed",
                error=f"train failed (rc={train.returncode}): {train.stdout[-500:]}",
            )
            return

        a1 = workdir / "a1.nam"
        if not a1.exists():
            _update(
                state,
                progress_cb,
                status="failed",
                error="train reported success but produced no a1.nam",
            )
            return

        job.out_dir.mkdir(parents=True, exist_ok=True)
        dest = job.out_dir / f"{state.name}.nam"
        try:
            shutil.copyfile(a1, dest)
        except Exception as e:
            _update(state, progress_cb, status="failed", error=f"copy failed: {e}")
            return

        fmt_text = distill_protocol.parse_format(train.stdout)
        _update(
            state,
            progress_cb,
            status="done",
            progress=1.0,
            detail=None,
            eta_seconds=None,
            output_path=str(dest),
            esr=distill_protocol.parse_esr(train.stdout),
            format_ok=distill_protocol.format_ok(fmt_text),
        )


def run_job(job: ConvertJob, progress_cb: ProgressCallback) -> ConvertJob:
    if job.output_format not in ("0.5x", "0.7.0"):
        raise ValueError(f"unknown output_format {job.output_format!r}")
    if not job.di_path.exists():
        raise FileNotFoundError(f"DI file not found at {job.di_path}")

    for state in job.files:
        if job.cancelled:
            if state.status not in ("done", "failed", "cancelled"):
                _update(
                    state, progress_cb, status="cancelled", error="cancelled by user"
                )
            continue
        try:
            _convert_one(state, job, progress_cb)
        except Exception as e:
            state.status = "failed"
            state.error = f"unexpected error: {e}"
            progress_cb(state)

    return job
