from __future__ import annotations

from pathlib import Path
import argparse
import json
import os
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
SYSTEMD_SRC = ROOT / "control/hourly/systemd"
USER_SYSTEMD = Path.home() / ".config/systemd/user"
EXECUTOR = "prediction-research-executor.service"
DIRECTOR = "prediction-research-hourly-director.service"
TIMER = "prediction-research-hourly-director.timer"
EXPECTED_AGENTS = {
    "discovery",
    "market_research",
    "mechanics",
    "algebra",
    "red_team_pentest",
    "research_director",
}


def run(args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=check,
    )


def validate_root() -> dict[str, object]:
    python = ROOT / ".venv/bin/python"
    required = [
        python,
        ROOT / "control/executor.py",
        ROOT / "control/hourly/edge_hunter_cycle.py",
        ROOT / "agents/registry.json",
        SYSTEMD_SRC / f"{EXECUTOR}.in",
        SYSTEMD_SRC / f"{DIRECTOR}.in",
        SYSTEMD_SRC / TIMER,
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise SystemExit("missing required runtime files: " + ", ".join(missing))

    registry = json.loads((ROOT / "agents/registry.json").read_text(encoding="utf-8"))
    roles = {str(item.get("id")) for item in registry.get("roles", [])}
    if roles != EXPECTED_AGENTS:
        raise SystemExit(
            "refusing service install: runtime is not E007 six-domain registry; "
            f"roles={sorted(roles)}"
        )
    if registry.get("live_trading") is not False:
        raise SystemExit("refusing service install: live_trading must remain false")
    if registry.get("paid_actions") is not False:
        raise SystemExit("refusing service install: paid_actions must remain false")
    if registry.get("wallet_actions") is not False:
        raise SystemExit("refusing service install: wallet_actions must remain false")

    git_root = run(["git", "rev-parse", "--show-toplevel"]).stdout.strip()
    if Path(git_root).resolve() != ROOT.resolve():
        raise SystemExit(f"repo root mismatch: {git_root} != {ROOT}")

    return {
        "root": str(ROOT),
        "python": str(python),
        "agents": sorted(roles),
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
        "openai_api": False,
    }


def render(template_name: str, python: Path) -> str:
    text = (SYSTEMD_SRC / template_name).read_text(encoding="utf-8")
    return (
        text.replace("@@ROOT@@", str(ROOT))
        .replace("@@PYTHON@@", str(python))
    )


def planned_units() -> dict[str, str]:
    python = ROOT / ".venv/bin/python"
    return {
        EXECUTOR: render(f"{EXECUTOR}.in", python),
        DIRECTOR: render(f"{DIRECTOR}.in", python),
        TIMER: (SYSTEMD_SRC / TIMER).read_text(encoding="utf-8"),
    }


def write_units(units: dict[str, str]) -> list[str]:
    USER_SYSTEMD.mkdir(parents=True, exist_ok=True)
    changed = []
    for name, content in units.items():
        target = USER_SYSTEMD / name
        old = target.read_text(encoding="utf-8") if target.exists() else None
        if old != content:
            tmp = target.with_suffix(target.suffix + ".tmp")
            tmp.write_text(content, encoding="utf-8")
            os.replace(tmp, target)
            changed.append(name)
    return changed


def unit_state(unit: str) -> dict[str, object]:
    proc = run(
        [
            "systemctl",
            "--user",
            "show",
            unit,
            "-p",
            "ActiveState",
            "-p",
            "SubState",
            "-p",
            "UnitFileState",
            "-p",
            "Result",
            "-p",
            "FragmentPath",
        ],
        check=False,
    )
    return {
        "rc": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def apply(run_now: bool) -> dict[str, object]:
    info = validate_root()
    units = planned_units()
    changed = write_units(units)

    run(["systemctl", "--user", "daemon-reload"])
    run(["systemctl", "--user", "enable", EXECUTOR])
    run(["systemctl", "--user", "restart", EXECUTOR])
    run(["systemctl", "--user", "enable", TIMER])
    run(["systemctl", "--user", "start", TIMER])

    director_started = False
    if run_now:
        # A direct start is intentionally opt-in. It exercises the same oneshot
        # used by the timer and does not grant any new execution authority.
        run(["systemctl", "--user", "start", DIRECTOR])
        director_started = True

    return {
        "schema": "PVA_RUNTIME_SERVICE_INSTALL_V1",
        "mode": "APPLY",
        "runtime": info,
        "changed_units": changed,
        "director_started_now": director_started,
        "units": {
            EXECUTOR: unit_state(EXECUTOR),
            DIRECTOR: unit_state(DIRECTOR),
            TIMER: unit_state(TIMER),
        },
        "guardrails": {
            "live_trading": False,
            "paid_actions": False,
            "wallet_actions": False,
            "openai_api": False,
        },
    }


def dry_run() -> dict[str, object]:
    info = validate_root()
    units = planned_units()
    return {
        "schema": "PVA_RUNTIME_SERVICE_INSTALL_V1",
        "mode": "DRY_RUN",
        "runtime": info,
        "targets": [str(USER_SYSTEMD / name) for name in units],
        "would_enable": [EXECUTOR, TIMER],
        "would_restart": [EXECUTOR],
        "guardrails": {
            "live_trading": False,
            "paid_actions": False,
            "wallet_actions": False,
            "openai_api": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Install supervised Prediction Research user services from this checkout."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write/reload/enable the user services. Without this flag only show the plan.",
    )
    parser.add_argument(
        "--run-now",
        action="store_true",
        help="With --apply, immediately start one Director cycle after service repair.",
    )
    args = parser.parse_args()

    if args.run_now and not args.apply:
        parser.error("--run-now requires --apply")

    result = apply(args.run_now) if args.apply else dry_run()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
