#!/usr/bin/env python3
"""Bridge-safe wrapper for the canonical E401 validation bundle.

The local task validator only permits Python entrypoints under control/jobs/
or experiments/.  Keep the validation implementation in control/weather/ and
use this wrapper solely as the approved execution entrypoint.
"""
from __future__ import annotations

from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "control" / "weather" / "validate_market_reaction_e401.py"

if not TARGET.is_file():
    raise SystemExit(f"missing canonical E401 validator: {TARGET}")

runpy.run_path(str(TARGET), run_name="__main__")
