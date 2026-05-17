"""Entry point so `python -m chronos_ingest <command>` works."""

from __future__ import annotations

import sys

from chronos_ingest.main import cli


if __name__ == "__main__":
    sys.exit(cli())
