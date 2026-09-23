#!/usr/bin/env python3
"""Canonical A19B-v2 live entrypoint with A19C clock evidence."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "control" / "weather"))

import clock_evidence_sntp_a19c as clock  # noqa: E402
import madis_ldm_queue_native_a19b_v2 as queue_native  # noqa: E402

# Explicit dependency injection: every live/replay ingest result carries the
# same A19C evidence schema. Replay remains ineligible by mode regardless.
queue_native.clock_health = clock.clock_health


if __name__ == "__main__":
    raise SystemExit(queue_native.main())
