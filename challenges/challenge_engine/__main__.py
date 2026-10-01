"""Entrypoint for `python -m challenge_engine`."""

from __future__ import annotations

import sys
from challenge_engine.cli import main

if __name__ == "__main__":
    sys.exit(main())
