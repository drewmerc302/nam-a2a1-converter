"""Single entry point that self-dispatches. Invoked as `python -m nam_a2a1 …` in a
source checkout, or as the frozen executable re-invoking itself.

    (no args) | serve     start the local web app + open the browser
    render  A2 DI OUT     render a DI through an A2 model -> teacher wav
    train   DI Y OUT ...  train + export an A1, transcode to 0.5.x
"""

import os
import sys


def _ensure_std_streams() -> None:
    """Guarantee sys.stdout/sys.stderr are real writable text streams, for every command.

    A windowed PyInstaller build (console=False) that Windows gives no console — the
    double-click case — starts with sys.stdout and sys.stderr set to None. Anything that
    touches them unguarded then dies before the app is up. That is not hypothetical: at
    `serve`, uvicorn's DefaultFormatter runs `sys.stdout.isatty()` while building its log
    config, so Config() raised "Unable to configure formatter 'default'" and the exe
    vanished on launch. Piping it (`nam-a2a1-converter.exe | Out-Host`) handed fd 1 a real
    pipe and masked the bug, which is exactly what the first Windows user hit.

    Prefer the inherited fd: the render/train workers ARE this exe, and the parent engine
    parses the stdout pipe it handed them, so emit_progress/emit_format must land there.
    Fall back to devnull only when the fd is genuinely unusable (no console, no pipe) —
    writes are then discarded, which is what a windowed app wants anyway.

    UTF-8 is forced so the console code page can't mangle worker output. Line buffering is
    load-bearing, not cosmetic: with stdout on a pipe CPython block-buffers at 8 KB, and
    only emit_progress passes flush=True.

    When a stream already exists (Linux and macOS always; console=True builds) reconfigure
    it in place rather than layering a second wrapper over the fd — two wrappers on one fd
    get finalized in unspecified order at exit, and if the original closes the fd first the
    other one's flush raises "Exception ignored ... Bad file descriptor" straight into the
    pipe the parent is parsing, which then lands in the user-visible error string.
    """
    for name, fd in (("stdout", 1), ("stderr", 2)):
        stream = getattr(sys, name)
        if stream is None:
            try:
                stream = os.fdopen(
                    fd, "w", encoding="utf-8", buffering=1, closefd=False
                )
                # Opening can succeed on a handle that is still unusable; isatty() is the
                # cheapest probe, and it is the exact call uvicorn makes.
                stream.isatty()
            except (OSError, ValueError):
                stream = open(os.devnull, "w", encoding="utf-8", buffering=1)
            setattr(sys, name, stream)
        else:
            try:
                stream.reconfigure(encoding="utf-8", line_buffering=True)
            except (AttributeError, OSError, ValueError):
                pass
        # Libraries that bypass the redirectable names and reach for the originals
        # (and PyInstaller's own excepthook) need these non-None too.
        if getattr(sys, f"__{name}__", None) is None:
            setattr(sys, f"__{name}__", getattr(sys, name))


def _selftest_headless_serve() -> None:
    """Regression guard for the windowed-launch crash, run inside the frozen exe in CI.

    CI always has a console, so `selftest` would otherwise never exercise the code path a
    double-clicking Windows user takes. Blank the streams the way that bootloader does and
    drive the call that actually broke — uvicorn's Config(), whose DefaultFormatter does
    `sys.stdout.isatty()`. Both branches of _ensure_std_streams are covered: fd usable, and
    fd unusable (no console, no pipe), the latter forced by making os.fdopen raise.
    """
    import uvicorn

    async def _dummy_app(scope, receive, send):  # pragma: no cover - never invoked
        raise NotImplementedError

    real_out, real_err, real_fdopen = sys.stdout, sys.stderr, os.fdopen
    for label, broken_fd in (("console", False), ("no-console", True)):
        try:
            sys.stdout = sys.stderr = None
            if broken_fd:
                os.fdopen = _raise_oserror
            _ensure_std_streams()
            if sys.stdout is None or sys.stderr is None:
                raise AssertionError(f"{label}: streams still None after repair")
            uvicorn.Config(_dummy_app, log_level="warning")
        finally:
            os.fdopen = real_fdopen
            sys.stdout, sys.stderr = real_out, real_err


def _raise_oserror(*_args, **_kwargs):
    raise OSError("selftest: simulated windowed build with no usable stdout")


def main() -> None:
    argv = sys.argv[1:]
    cmd = argv[0] if argv else "serve"

    _ensure_std_streams()

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
        _selftest_headless_serve()
        print("selftest OK")
    elif cmd in ("serve", ""):
        from nam_a2a1.server import serve

        serve()
    else:
        sys.exit(f"unknown command {cmd!r} (expected serve|render|train|selftest)")


if __name__ == "__main__":
    main()
