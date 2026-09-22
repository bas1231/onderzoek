from __future__ import annotations

from pathlib import Path
import json
import subprocess


ROOT = Path(__file__).resolve().parents[2]
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


def run(args: list[str]) -> dict[str, object]:
    proc = subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "rc": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def read_unit(name: str) -> str:
    path = USER_SYSTEMD / name
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def property_map(unit: str, properties: list[str]) -> dict[str, str]:
    args = ["systemctl", "--user", "show", unit]
    for prop in properties:
        args.extend(["-p", prop])
    result = run(args)
    values: dict[str, str] = {}
    if result["rc"] == 0:
        for line in str(result["stdout"]).splitlines():
            key, sep, value = line.partition("=")
            if sep:
                values[key] = value
    return values


def main() -> int:
    registry = json.loads((ROOT / "agents/registry.json").read_text(encoding="utf-8"))
    roles = {str(item.get("id")) for item in registry.get("roles", [])}

    executor_text = read_unit(EXECUTOR)
    director_text = read_unit(DIRECTOR)
    timer_text = read_unit(TIMER)

    executor = property_map(
        EXECUTOR,
        ["ActiveState", "SubState", "UnitFileState", "Result", "FragmentPath"],
    )
    director = property_map(
        DIRECTOR,
        ["ActiveState", "SubState", "Result", "FragmentPath"],
    )
    timer = property_map(
        TIMER,
        [
            "ActiveState",
            "SubState",
            "UnitFileState",
            "Result",
            "LastTriggerUSec",
            "NextElapseUSecRealtime",
            "FragmentPath",
        ],
    )

    root_token = str(ROOT)
    checks = {
        "e007_registry_exact": roles == EXPECTED_AGENTS,
        "executor_unit_uses_current_root": root_token in executor_text,
        "director_unit_uses_current_root": root_token in director_text,
        "executor_supervised_restart": "Restart=always" in executor_text,
        "timer_hourly": "OnCalendar=*-*-* *:00:00" in timer_text,
        "timer_persistent": "Persistent=true" in timer_text,
        "executor_active": executor.get("ActiveState") == "active",
        "executor_enabled": executor.get("UnitFileState") == "enabled",
        "timer_active": timer.get("ActiveState") == "active",
        "timer_enabled": timer.get("UnitFileState") == "enabled",
        "live_trading_false": registry.get("live_trading") is False,
        "paid_actions_false": registry.get("paid_actions") is False,
        "wallet_actions_false": registry.get("wallet_actions") is False,
    }
    ok = all(checks.values())

    result = {
        "schema": "PVA_RUNTIME_SERVICE_HEALTH_V1",
        "ok": ok,
        "root": root_token,
        "checks": checks,
        "executor": executor,
        "director": director,
        "timer": timer,
        "agents": sorted(roles),
        "guardrails": {
            "live_trading": False,
            "paid_actions": False,
            "wallet_actions": False,
            "openai_api": False,
        },
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
