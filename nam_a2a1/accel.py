"""Answers one question for the UI: is this machine training on a GPU, and if not,
could it be?

Two independent facts have to be combined, because either one alone misleads:

  1. What the *bundled* torch can do. The CPU wheel contains no CUDA kernels at all,
     so torch.cuda.is_available() is False on a machine with a perfectly good RTX card.
     The default builds ship that wheel deliberately — the CUDA wheel is ~2.6 GB against
     ~122 MB, which is not a cost to impose on the Mac/AMD/Intel majority.
  2. What hardware is actually present. nvidia-smi ships with the NVIDIA driver, so it
     answers this WITHOUT torch and regardless of which wheel we froze.

Fact 1 comes from a short-lived worker subprocess (`<exe> accel`) rather than importing
torch in this process. The UI process would otherwise carry torch's RSS for the whole
session, on top of the worker that already loads it during a convert — and this is the
same self-invoking worker pattern engine.py uses, so it costs no new machinery.

When 2 says "NVIDIA present" and 1 says "CPU-only build", the user is leaving a large
speedup on the table and the UI points them at the CUDA download.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from typing import Optional

# Maxwell. Modern torch CUDA wheels no longer emit kernels below this, so a card under
# it would install the 2.6 GB build and still fall back to CPU.
MIN_COMPUTE_CAPABILITY = 5.0

# Training a NAM net is tiny; VRAM is not the binding constraint. This only screens out
# display adapters too small to hold the model plus a batch at all.
MIN_VRAM_MB = 1800

# Platforms a CUDA build exists for. macOS is absent on purpose and always will be:
# there are no CUDA torch wheels for macOS at any version, so an NVIDIA card in an old
# Intel Mac (or an eGPU) has no upgrade path and must not be advertised one.
#
# Before this list existed the banner keyed only off "NVIDIA card present + this build
# has no CUDA", which is platform-blind — a Linux user with an RTX 3060 was shown "Get
# the CUDA build" and sent to a page whose only Linux asset was the CPU build they had
# already downloaded (reported 2026-07-28).
CUDA_PLATFORMS = ("win32", "linux")

# The README section, NOT the bare releases page. Every CUDA bundle ships as numbered
# parts that have to be rejoined before they are usable, and the releases page says
# nothing about that — it just shows a list of .001/.002 files. The README names the
# right file for each OS and gives the rejoin command.
CUDA_DOWNLOAD_URL = "https://github.com/drewmerc302/nam-a2a1-converter#gpu-acceleration"

_cache: Optional[dict] = None
_cache_lock = threading.Lock()


def _no_window_kwargs() -> dict:
    """Windows: keep a windowed build from flashing a console for each probe."""
    if os.name == "nt":
        return {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)}
    return {}


def probe_torch() -> dict:
    """Ask the real bundled torch what it can do, via a throwaway worker process."""
    from nam_a2a1.engine import _worker_base, _worker_env

    try:
        out = subprocess.run(
            [*_worker_base(), "accel"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            env=_worker_env(),
            **_no_window_kwargs(),
        )
        # The worker prints one JSON line; tolerate warnings on the same stream.
        for line in reversed(out.stdout.splitlines()):
            line = line.strip()
            if line.startswith("{"):
                return json.loads(line)
    except (OSError, subprocess.SubprocessError, ValueError):
        pass
    return {"backend": "unknown", "cuda_build": False, "torch": None}


def detect_nvidia() -> Optional[dict]:
    """Read the card out of nvidia-smi. None when there is no NVIDIA driver.

    compute_cap is a newer --query-gpu field than the rest; if this nvidia-smi is too
    old to know it the whole query errors, so fall back to a query without it rather
    than concluding there is no GPU.
    """
    for fields in ("name,compute_cap,memory.total", "name,memory.total"):
        try:
            out = subprocess.run(
                [
                    "nvidia-smi",
                    f"--query-gpu={fields}",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=10,
                **_no_window_kwargs(),
            )
        except (OSError, subprocess.SubprocessError):
            return None  # no driver installed -> no nvidia-smi on PATH
        if out.returncode != 0 or not out.stdout.strip():
            continue
        # Multi-GPU machines print one row per card; the first is enough to advise.
        parts = [p.strip() for p in out.stdout.strip().splitlines()[0].split(",")]
        if "compute_cap" in fields and len(parts) >= 3:
            name, cap, vram = parts[0], parts[1], parts[2]
        elif len(parts) >= 2:
            name, cap, vram = parts[0], "", parts[1]
        else:
            continue
        return {
            "name": name,
            "compute_capability": _to_float(cap),
            "vram_mb": _to_float(vram),
        }
    return None


def _to_float(value: str) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _card_is_supported(gpu: dict) -> bool:
    """Unknown fields count as supported: an old nvidia-smi that can't report
    compute_cap is not evidence of a weak card, and steering someone away from a
    working speedup is the worse error here."""
    cap = gpu.get("compute_capability")
    vram = gpu.get("vram_mb")
    if cap is not None and cap < MIN_COMPUTE_CAPABILITY:
        return False
    if vram is not None and vram < MIN_VRAM_MB:
        return False
    return True


def status(refresh: bool = False) -> dict:
    """Cached. The answer can only change if the user installs a driver or a different
    build, neither of which happens while the app is running."""
    global _cache
    with _cache_lock:
        if _cache is not None and not refresh:
            return _cache

    torch_info = probe_torch()
    gpu = detect_nvidia()
    backend = torch_info.get("backend", "unknown")

    # Only worth nagging when there is a real speedup being missed AND the user can
    # actually act on it: a supported NVIDIA card, a build that physically cannot use
    # it, and a platform a CUDA bundle is published for. Dropping that last clause is
    # what made the banner a dead end on Linux.
    upgrade = bool(
        gpu
        and _card_is_supported(gpu)
        and not torch_info.get("cuda_build")
        and backend not in ("cuda", "mps")
        and sys.platform.startswith(CUDA_PLATFORMS)
    )

    result = {
        "backend": backend,
        "cuda_build": bool(torch_info.get("cuda_build")),
        "torch": torch_info.get("torch"),
        "gpu": gpu,
        "platform": sys.platform,
        "upgrade_available": upgrade,
        "download_url": CUDA_DOWNLOAD_URL if upgrade else None,
    }
    with _cache_lock:
        _cache = result
    return result
