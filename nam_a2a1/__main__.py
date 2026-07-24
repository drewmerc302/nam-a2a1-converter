"""Single entry point that self-dispatches. Invoked as `python -m nam_a2a1 …` in a
source checkout, or as the frozen executable re-invoking itself.

    (no args) | serve     start the local web app + open the browser
    render  A2 DI OUT     render a DI through an A2 model -> teacher wav
    train   DI Y OUT ...  train + export an A1, transcode to 0.5.x
"""

import os
import sys


def _reopen_stdout_utf8() -> None:
    """A windowed PyInstaller build (console=False) sets sys.stdout to None, but the
    parent engine hands render/train workers a pipe on fd 1 and parses their stdout.
    Reopen fd 1 as UTF-8 so emit_progress/emit_format/print reach the parent on every
    OS, regardless of the windowed bootloader or the console code page."""
    try:
        sys.stdout = os.fdopen(1, "w", encoding="utf-8", buffering=1, closefd=False)
    except OSError:
        pass


def main() -> None:
    argv = sys.argv[1:]
    cmd = argv[0] if argv else "serve"

    if cmd in ("render", "train"):
        _reopen_stdout_utf8()

    if cmd == "render":
        from nam_a2a1.pipeline import render_a2

        sys.argv = ["render", *argv[1:]]
        render_a2.main()
    elif cmd == "train":
        from nam_a2a1.pipeline import train_a1_070

        sys.argv = ["train", *argv[1:]]
        train_a1_070.main()
    elif cmd in ("serve", ""):
        from nam_a2a1.server import serve

        serve()
    else:
        sys.exit(f"unknown command {cmd!r} (expected serve|render|train)")


if __name__ == "__main__":
    main()
