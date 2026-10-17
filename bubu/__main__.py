"""Allow running the buddy with ``python -m bubu``."""

from .app import main

if __name__ == "__main__":
    raise SystemExit(main())
