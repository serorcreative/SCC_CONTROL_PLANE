"""Permet ``python -m scc_control_plane``."""

from __future__ import annotations

import sys

from scc_control_plane.cli import main

if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
