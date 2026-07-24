"""PyInstaller entry point. The frozen executable runs this; it self-dispatches on
argv the same way `python -m nam_a2a1` does (serve / render / train)."""

from nam_a2a1.__main__ import main

if __name__ == "__main__":
    main()
