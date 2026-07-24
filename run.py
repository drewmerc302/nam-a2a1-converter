"""PyInstaller entry point. The frozen executable runs this; it self-dispatches on
argv the same way `python -m nam_a2a1` does (serve / render / train)."""

import multiprocessing

from nam_a2a1.__main__ import main

if __name__ == "__main__":
    # Windows and macOS default the multiprocessing start method to "spawn", which
    # re-executes this frozen exe. Without this, any spawn from torch/BLAS re-enters
    # the app instead of the worker pool. Must be the first thing that runs.
    multiprocessing.freeze_support()
    main()
