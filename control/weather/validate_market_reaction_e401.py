#!/usr/bin/env python3
"""Local, no-network validation bundle for E401 capture/analyzer code."""
from __future__ import annotations

import json
from pathlib import Path
import py_compile
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
FILES = [
    ROOT / "control/weather/market_reaction.py",
    ROOT / "control/weather/test_market_reaction.py",
    ROOT / "control/weather/kalshi_market_reaction_recorder.py",
    ROOT / "control/weather/kalshi_market_reaction_ws.py",
    ROOT / "control/weather/analyze_kwi_market_reaction.py",
    ROOT / "control/weather/test_market_reaction_ws.py",
    ROOT / "control/weather/test_analyze_kwi_market_reaction.py",
]
TESTS = [
    ROOT / "control/weather/test_market_reaction.py",
    ROOT / "control/weather/test_market_reaction_ws.py",
    ROOT / "control/weather/test_analyze_kwi_market_reaction.py",
]


def main() -> int:
    compile_results = []
    for path in FILES:
        py_compile.compile(str(path), doraise=True)
        compile_results.append(str(path.relative_to(ROOT)))

    tests = []
    ok = True
    for path in TESTS:
        proc = subprocess.run(
            [sys.executable, str(path)], cwd=ROOT,
            capture_output=True, text=True, timeout=60,
        )
        tests.append({
            "path": str(path.relative_to(ROOT)),
            "returncode": proc.returncode,
            "stdout_tail": proc.stdout[-2000:],
            "stderr_tail": proc.stderr[-2000:],
        })
        ok = ok and proc.returncode == 0

    report = {
        "task": "KAL-WX-MARKET-REACTION-E401-VALIDATION",
        "compile_pass": True,
        "compiled": compile_results,
        "tests": tests,
        "tests_pass": ok,
        "live_trading": False,
        "paid_action": False,
        "wallet_action": False,
        "economic_conclusion": "NO_PROVEN_EDGE",
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    if not ok:
        raise SystemExit(1)
    print("KWI_MARKET_REACTION_E401_VALIDATION_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
