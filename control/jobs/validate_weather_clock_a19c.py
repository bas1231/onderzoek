#!/usr/bin/env python3
"""A19C clock-evidence gate for Weather Runner.

This validator does not install or configure time-sync software. It proves the
clock-evidence semantics locally and then inventories the host clock. A host
without eligible offset/uncertainty evidence is a valid terminal research gate,
not a build failure.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
WEATHER = ROOT / "control" / "weather"
sys.path.insert(0, str(WEATHER))

import madis_ldm_ingest_a19b as clockmod  # noqa: E402

EVIDENCE = ROOT / "evidence" / "weather" / "WEATHER-CLOCK-A19C-latest.json"


def parsed(text: str) -> dict:
    return clockmod.parse_chronyc_tracking(text)


def main() -> int:
    result: dict = {
        "task": "WEATHER-CLOCK-A19C",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "economic_conclusion": "NO_PROVEN_EDGE",
        "live_trading": False,
        "paid_action": False,
        "wallet_action": False,
        "system_changes": False,
        "checks": {},
    }

    # CHECK 1/3 — technical/regression: healthy chrony evidence must be parsed.
    try:
        source = (WEATHER / "madis_ldm_ingest_a19b.py").read_text(encoding="utf-8")
        compile(source, str(WEATHER / "madis_ldm_ingest_a19b.py"), "exec")
        good = parsed(
            "Reference ID    : 1.2.3.4\n"
            "Stratum         : 3\n"
            "System time     : 0.000250 seconds slow of NTP time\n"
            "Last offset     : -0.000100 seconds\n"
            "RMS offset      : 0.000300 seconds\n"
            "Root delay      : 0.010000 seconds\n"
            "Root dispersion : 0.002000 seconds\n"
            "Leap status     : Normal\n"
        )
        check1 = bool(
            good.get("evidence_clock_eligible") is True
            and round(float(good["clock_offset_ms"]), 6) == -0.25
            and round(float(good["clock_uncertainty_ms"]), 6) == 7.25
            and good.get("stratum") == 3
        )
        result["checks"]["check_1_technical"] = {
            "pass": check1,
            "compile_pass": True,
            "synthetic_good": good,
        }
    except Exception as exc:
        check1 = False
        result["checks"]["check_1_technical"] = {
            "pass": False,
            "detail": f"{type(exc).__name__}: {exc}",
        }

    # CHECK 2/3 — adversarial/fail-closed semantics.
    adversarial = {}
    if check1:
        cases = {
            "excess_uncertainty": (
                "Reference ID    : 1.2.3.4\n"
                "Stratum         : 3\n"
                "System time     : 0.001 seconds fast of NTP time\n"
                "Root delay      : 0.400 seconds\n"
                "Root dispersion : 0.200 seconds\n"
                "Leap status     : Normal\n"
            ),
            "bad_leap_status": (
                "Reference ID    : 1.2.3.4\n"
                "Stratum         : 3\n"
                "System time     : 0.000001 seconds fast of NTP time\n"
                "Root delay      : 0.001 seconds\n"
                "Root dispersion : 0.001 seconds\n"
                "Leap status     : Not synchronised\n"
            ),
            "missing_uncertainty_components": (
                "Reference ID    : 1.2.3.4\n"
                "Stratum         : 3\n"
                "System time     : 0.000001 seconds fast of NTP time\n"
                "Leap status     : Normal\n"
            ),
        }
        check2 = True
        for name, text in cases.items():
            out = parsed(text)
            rejected = out.get("evidence_clock_eligible") is False
            adversarial[name] = {"rejected": rejected, "parsed": out}
            check2 = check2 and rejected
    else:
        check2 = False
    result["checks"]["check_2_fail_closed"] = {
        "pass": check2,
        "cases": adversarial,
        **({"status": "SKIPPED_CHECK_1_FAILED"} if not check1 else {}),
    }

    # CHECK 3/3 — realistic local host inventory. Eligibility is NOT required
    # for this check to pass: an explicit BLOCKED_CLOCK_EVIDENCE is valid.
    if check1 and check2:
        try:
            real = clockmod.clock_health()
            required = {
                "clock_source",
                "clock_offset_ms",
                "clock_uncertainty_ms",
                "evidence_clock_eligible",
            }
            structurally_valid = required.issubset(real)
            eligible = real.get("evidence_clock_eligible") is True
            if eligible:
                structurally_valid = bool(
                    structurally_valid
                    and real.get("clock_offset_ms") is not None
                    and real.get("clock_uncertainty_ms") is not None
                    and float(real["clock_uncertainty_ms"]) <= clockmod.CLOCK_MAX_UNCERTAINTY_MS
                )
            check3 = structurally_valid
            result["checks"]["check_3_real_host"] = {
                "pass": check3,
                "clock_evidence_eligible": eligible,
                "clock_health": real,
            }
        except Exception as exc:
            check3 = False
            eligible = False
            result["checks"]["check_3_real_host"] = {
                "pass": False,
                "detail": f"{type(exc).__name__}: {exc}",
            }
    else:
        check3 = False
        eligible = False
        result["checks"]["check_3_real_host"] = {
            "pass": False,
            "status": "SKIPPED_EARLIER_CHECK_FAILED",
        }

    local_pass = bool(check1 and check2 and check3)
    result["status"] = "PASS_LOCAL_BUILD" if local_pass else "BLOCKED_LOCAL_VALIDATION"
    if not local_pass:
        result["next_gate"] = "FIX_A19C_CLOCK_VALIDATION"
        result["terminal_for_current_authorization"] = False
    elif eligible:
        result["next_gate"] = "CLOCK_EVIDENCE_READY_FOR_QUEUE_NATIVE_CAPTURE"
        result["terminal_for_current_authorization"] = False
    else:
        result["next_gate"] = "BLOCKED_CLOCK_EVIDENCE"
        result["terminal_for_current_authorization"] = True

    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if local_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
