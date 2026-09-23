#!/usr/bin/env python3
"""Passive clock-evidence diagnostic for Weather A19B-v2.

This module never changes system time, installs software, or starts services.
It distinguishes "the OS says NTP is synchronized" from quantitative clock
proof suitable for sub-second latency evidence.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
from typing import Callable

from madis_ldm_ingest_a19b import parse_chronyc_tracking

MAX_RAW_CHARS = 4000
SYNC_MARKER = Path("/run/systemd/timesync/synchronized")


def _run(args: list[str], timeout: int = 5) -> dict:
    try:
        cp = subprocess.run(args, text=True, capture_output=True, timeout=timeout)
        return {
            "command": args,
            "returncode": cp.returncode,
            "stdout": cp.stdout[-MAX_RAW_CHARS:],
            "stderr": cp.stderr[-MAX_RAW_CHARS:],
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": args,
            "returncode": 124,
            "stdout": (exc.stdout or "")[-MAX_RAW_CHARS:] if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "")[-MAX_RAW_CHARS:] if isinstance(exc.stderr, str) else "",
            "timed_out": True,
        }
    except Exception as exc:
        return {
            "command": args,
            "returncode": None,
            "stdout": "",
            "stderr": f"{type(exc).__name__}: {exc}"[-MAX_RAW_CHARS:],
            "timed_out": False,
        }


def assess_chronyc_tracking(text: str) -> dict:
    """Return quantitative evidence only when the existing strict parser allows it."""
    parsed = parse_chronyc_tracking(text)
    eligible = parsed.get("evidence_clock_eligible") is True
    return {
        "clock_source": parsed.get("clock_source"),
        "clock_offset_ms": parsed.get("clock_offset_ms"),
        "clock_uncertainty_ms": parsed.get("clock_uncertainty_ms"),
        "clock_evidence_eligible": eligible,
        "stratum": parsed.get("stratum"),
        "leap_status": parsed.get("leap_status"),
        "root_delay_ms": parsed.get("root_delay_ms"),
        "root_dispersion_ms": parsed.get("root_dispersion_ms"),
        "uncertainty_semantics": parsed.get("clock_uncertainty_semantics"),
        "reason": "QUANTITATIVE_CHRONY_EVIDENCE_PASS" if eligible else "CHRONY_EVIDENCE_INSUFFICIENT",
    }


def assess_inventory(*, chrony: dict | None, ntp_synchronized: bool | None, ntp_enabled: bool | None, sync_marker: bool) -> dict:
    """Combine passive observations without upgrading qualitative sync to latency proof."""
    if chrony and chrony.get("clock_evidence_eligible") is True:
        return {
            **chrony,
            "ntp_synchronized": ntp_synchronized,
            "ntp_enabled": ntp_enabled,
            "systemd_timesync_marker": sync_marker,
            "status": "PASS_CLOCK_EVIDENCE",
            "next_gate": "CLOCK_EVIDENCE_SATISFIED",
        }
    return {
        "clock_source": chrony.get("clock_source") if chrony else ("timedatectl" if ntp_synchronized is not None else None),
        "clock_offset_ms": chrony.get("clock_offset_ms") if chrony else None,
        "clock_uncertainty_ms": chrony.get("clock_uncertainty_ms") if chrony else None,
        "clock_evidence_eligible": False,
        "ntp_synchronized": ntp_synchronized,
        "ntp_enabled": ntp_enabled,
        "systemd_timesync_marker": sync_marker,
        "status": "BLOCKED_CLOCK_EVIDENCE",
        "next_gate": "OBTAIN_QUANTITATIVE_CLOCK_OFFSET_AND_UNCERTAINTY_EVIDENCE",
        "reason": (chrony or {}).get("reason") or "QUALITATIVE_SYNC_ONLY_OR_NO_QUANTITATIVE_SOURCE",
    }


def _parse_yes_no(raw: str) -> bool | None:
    value = raw.strip().lower()
    if value in {"yes", "true", "1"}:
        return True
    if value in {"no", "false", "0"}:
        return False
    return None


def collect_clock_evidence(
    *,
    which: Callable[[str], str | None] = shutil.which,
    runner: Callable[[list[str], int], dict] = _run,
    sync_marker: Path = SYNC_MARKER,
) -> dict:
    inventory: dict = {
        "chronyc_path": which("chronyc"),
        "timedatectl_path": which("timedatectl"),
        "commands": {},
    }

    chrony_assessment = None
    if inventory["chronyc_path"]:
        raw = runner([str(inventory["chronyc_path"]), "tracking", "-n"], 5)
        inventory["commands"]["chronyc_tracking"] = raw
        if raw.get("returncode") == 0 and str(raw.get("stdout") or "").strip():
            chrony_assessment = assess_chronyc_tracking(str(raw["stdout"]))
        else:
            chrony_assessment = {
                "clock_source": "chrony",
                "clock_offset_ms": None,
                "clock_uncertainty_ms": None,
                "clock_evidence_eligible": False,
                "reason": "CHRONYC_TRACKING_UNAVAILABLE",
            }

    ntp_sync = None
    ntp_enabled = None
    if inventory["timedatectl_path"]:
        td = str(inventory["timedatectl_path"])
        raw_sync = runner([td, "show", "-p", "NTPSynchronized", "--value"], 5)
        inventory["commands"]["timedatectl_ntp_synchronized"] = raw_sync
        if raw_sync.get("returncode") == 0:
            ntp_sync = _parse_yes_no(str(raw_sync.get("stdout") or ""))
        raw_ntp = runner([td, "show", "-p", "NTP", "--value"], 5)
        inventory["commands"]["timedatectl_ntp_enabled"] = raw_ntp
        if raw_ntp.get("returncode") == 0:
            ntp_enabled = _parse_yes_no(str(raw_ntp.get("stdout") or ""))

    try:
        marker_present = sync_marker.exists()
    except OSError:
        marker_present = False

    assessment = assess_inventory(
        chrony=chrony_assessment,
        ntp_synchronized=ntp_sync,
        ntp_enabled=ntp_enabled,
        sync_marker=marker_present,
    )
    return {
        "schema": "WEATHER_CLOCK_EVIDENCE_A19B_V2_V1",
        "passive_only": True,
        "system_modified": False,
        "assessment": assessment,
        "inventory": inventory,
    }


if __name__ == "__main__":
    result = collect_clock_evidence()
    print(json.dumps(result, indent=2, sort_keys=True))
