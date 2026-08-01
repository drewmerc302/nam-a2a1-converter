"""Teacher-render gain: the sidecar contract between Stage 1 and Stage 2.

Why this exists
---------------
NAM's `Dataset` refuses any target that reaches digital full scale::

    if _torch.abs(y).max() >= 1.0:
        raise ValueError("Output clipped.")          # nam/data.py

Stage 1 writes the teacher render as 24-bit PCM, and a 24-bit write pins every
sample at or below -1.0 to exactly int -8388608, which NAM reads back as
exactly -1.0. So a *single* negative sample at the rail is enough to kill the
whole conversion — which is why hot captures (high-gain amps, boosted drives)
failed while quieter ones converted fine. Note the asymmetry: the positive rail
lands on 0.99999988 and never trips the check.

The fix is to attenuate y before writing it, record the gain here, and undo it
on the exported student. The undo is exactly what NAM's own
`Dataset._ScaleOutputHook` does for datasets it scaled itself: for a WaveNet the
output is linear in `head_scale`, and `head_scale` is stored twice in a .nam —
in `config` and as `weights[-1]` — so scaling both is a lossless level change,
not a retrain.

stdlib-only: imported by both pipeline stages.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, Union

# Ceiling for the written teacher render. Below the 24-bit rails with enough
# margin that quantization can't round a sample onto them.
PEAK_CEILING = 0.98

_PathLike = Union[str, Path]


def gain_for_peak(peak: float) -> float:
    """Attenuation to apply to a render whose absolute peak is `peak`.

    1.0 (a no-op) for anything already under the ceiling, so ordinary captures
    keep their exact original level and byte-identical behaviour.
    """
    if not math.isfinite(peak) or peak <= PEAK_CEILING:
        return 1.0
    return PEAK_CEILING / peak


def sidecar_path(y_path: _PathLike) -> Path:
    p = Path(y_path)
    return p.with_name(p.name + ".gain.json")


def write_gain(y_path: _PathLike, gain: float, source_peak: float) -> Path:
    path = sidecar_path(y_path)
    path.write_text(
        json.dumps({"y_gain": gain, "source_peak": source_peak}), encoding="utf-8"
    )
    return path


def read_gain(y_path: _PathLike) -> float:
    """Gain Stage 1 applied to `y_path`, or 1.0 if there's no usable sidecar.

    Missing/garbage sidecar means "nothing was attenuated" — that keeps the
    stage-2 CLI usable standalone against a hand-made y.wav.
    """
    try:
        data = json.loads(sidecar_path(y_path).read_text(encoding="utf-8"))
        gain = float(data["y_gain"])
    except (OSError, ValueError, TypeError, KeyError):
        return 1.0
    if not math.isfinite(gain) or gain <= 0.0:
        return 1.0
    return gain


def compensate_model_dict(model: Dict[str, Any], gain: float) -> Dict[str, Any]:
    """Undo a Stage 1 attenuation of `gain` on an exported WaveNet .nam dict.

    Mutates and returns `model`. Raises if the file doesn't carry `head_scale`
    in both places, rather than shipping a model at the wrong level.
    """
    if gain == 1.0:
        return model
    scale = 1.0 / gain
    config = model["config"]
    head_scale = float(config["head_scale"])
    tail = float(model["weights"][-1])
    if not math.isclose(head_scale, tail, rel_tol=1e-5, abs_tol=1e-8):
        raise ValueError(
            "export layout changed: config head_scale "
            f"{head_scale} != weights[-1] {tail}; refusing to rescale"
        )
    config["head_scale"] = head_scale * scale
    model["weights"][-1] = tail * scale
    metadata = model.get("metadata")
    if isinstance(metadata, dict) and "loudness" in metadata:
        metadata["loudness"] += 20.0 * math.log10(scale)
    return model


def compensate_file(nam_path: _PathLike, gain: float) -> float:
    """Apply `compensate_model_dict` to a .nam in place. Returns the gain used."""
    if gain == 1.0:
        return gain
    path = Path(nam_path)
    with open(path, encoding="utf-8") as fp:
        model = json.load(fp)
    compensate_model_dict(model, gain)
    with open(path, "w", encoding="utf-8") as fp:
        json.dump(model, fp)
    return gain
