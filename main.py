"""Executable entry point used by PyInstaller builds.

``python -m bubu`` is the normal way to run from source; this file exists so
PyInstaller has a top-level script whose imports resolve trivially.
"""

from bubu.app import main

if __name__ == "__main__":
    raise SystemExit(main())
