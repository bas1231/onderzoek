"""Read-only classifier of installed browser-launch registration support.

This reports only capabilities and version labels from allowlisted Prediction
runtime source. It never reads token/credential paths, imports runtime code,
registers a launcher, starts a session, or modifies bridge/executor state.
"""
from __future__ import annotations

from pathlib import Path
import re

RUNTIME = Path(".local/share/prediction-chat-bridge")
FILES = (
    "bridge_server.py",
    "bridge_server_session_bootstrap.py",
    "prediction-chat-wake.user.js",
)


def classify(home: Path) -> tuple[int, str]:
    root = home / RUNTIME
    labels = []
    server_capable = False
    bootstrap_capable = False
    unsafe_path = False
    for name in FILES:
        file = root / name
        label = name.replace(".", "_").replace("-", "_")
        if file.is_symlink():
            labels.append(label + "=SYMLINK_REFUSED")
            unsafe_path = True
            continue
        if not file.is_file():
            labels.append(label + "=MISSING")
            continue
        if file.stat().st_size > 350000:
            labels.append(label + "=OVERSIZED_REFUSED")
            unsafe_path = True
            continue
        text = file.read_text(encoding="utf-8")
        if name == "bridge_server.py":
            has_import = "bridge_server_session_bootstrap" in text
            has_handler = "/dashboard-launcher/register" in text
            server_capable = has_import or has_handler
            labels.append(label + "=" + ("SESSION_CAPABLE" if server_capable else "NO_REGISTRATION_REFERENCE"))
        elif name == "bridge_server_session_bootstrap.py":
            supports = "/dashboard-launcher/register" in text and "register_dashboard_launcher" in text
            labels.append(label + "=" + ("REGISTRATION_ENDPOINT_PRESENT" if supports else "REGISTRATION_ENDPOINT_ABSENT"))
            bootstrap_capable = supports
        else:
            match = re.search(r"(?:@version\s+|SCRIPT_VERSION\s*=\s*['\"])([0-9]+(?:\.[0-9]+){1,3})", text)
            version = match.group(1) if match else "UNKNOWN"
            supports = "/dashboard-launcher/register" in text
            labels.append(label + "=" + ("REGISTRATION_CODE_" if supports else "NO_REGISTRATION_CODE_") + version)
    # Each prerequisite must independently pass. A missing/symlinked bootstrap
    # cannot inherit success from a previously inspected server wrapper.
    server_ok = server_capable and bootstrap_capable and not unsafe_path
    return (0 if server_ok else 2), "LAUNCH_REG_RUNTIME=" + ",".join(labels)


if __name__ == "__main__":
    try:
        rc, result = classify(Path.home())
    except (OSError, UnicodeError, ValueError):
        rc, result = 2, "LAUNCH_REG_RUNTIME=READ_UNAVAILABLE"
    print(result, flush=True)
    raise SystemExit(rc)
