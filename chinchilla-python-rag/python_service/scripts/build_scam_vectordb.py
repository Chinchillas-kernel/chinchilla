#!/usr/bin/env python3
"""
CLI wrapper for the unified scam defense ingestion pipeline.

Delegates to `agent.tools.scam_data_ingest.main` so that the CLI in scripts/
remains available while all ingestion logic lives in a single shared module.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional, Sequence

# Ensure project root is on sys.path for module imports
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent.tools import scam_data_ingest


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Delegate to the shared ingestion CLI."""
    return scam_data_ingest.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
