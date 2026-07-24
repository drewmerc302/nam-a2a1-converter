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
    Make fd 1 a line-buffered UTF-8 text stream so emit_progress/emit_format/print reach
    the parent on every OS, regardless of the windowed bootloader or the console code
    page. Line buffering is load-bearing, not cosmetic: with stdout on a pipe CPython
    block-buffers at 8 KB, and only emit_progress passes flush=True.

    When stdout already exists (Linux and macOS always; console=True builds) reconfigure
    it in place rather than layering a second wrapper over fd 1 — two wrappers on one fd
    get finalized in unspecified order at exit, and if the original closes fd 1 first the
    other one's flush raises "Exception ignored ... Bad file descriptor" straight into the
    pipe the parent is parsing, which then lands in the user-visible error string."""
    if sys.stdout is None:
        try:
            sys.stdout = os.fdopen(1, "w", encoding="utf-8", buffering=1, closefd=False)
        except OSError:
            pass
    else:
        try:
            sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
        except (AttributeError, OSError, ValueError):
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
    elif cmd == "selftest":
        # Force the full import graph so a frozen build fails HERE (runnable in CI)
        # on any missing bundled module, instead of at a user's first convert.
        import importlib

        for mod in (
            "nam_a2a1.server",
            "nam_a2a1.engine",
            "nam_a2a1.api",
            "nam_a2a1.pipeline.render_a2",
            "nam_a2a1.pipeline.train_a1_070",
            "nam_a2a1.pipeline.nam_transcode",
            "nam_a2a1.pipeline.distill_protocol",
        ):
            importlib.import_module(mod)
        print("selftest OK")
    elif cmd in ("serve", ""):
        from nam_a2a1.server import serve

        serve()
    else:
        sys.exit(f"unknown command {cmd!r} (expected serve|render|train|selftest)")


if __name__ == "__main__":
    main()
