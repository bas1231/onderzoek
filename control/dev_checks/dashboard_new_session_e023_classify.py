from __future__ import annotations

import io
import unittest
from pathlib import Path

ROOT = Path("control/tampermonkey_multichat")
FILES = [
  "test_active_page_routing.py",
  "test_bridge_ping_status_compaction.py",
  "test_bridge_server_hardened.py",
  "test_bridge_server_sent_semantics.py",
  "test_dashboard_new_session_launch.py",
  "test_install_hardened_bridge_fast_deadman_static.py",
  "test_nightshift_wsl_transport_static.py",
  "test_patch_v045_task_dedupe_static.py",
  "test_route_consumer_resilience.py",
  "test_session_route_bootstrap.py",
  "test_status_compaction_nested.py",
  "test_userscript_delivery_dedupe_static.py",
  "test_userscript_v046_guard_static.py",
  "test_v04x_task_dedupe_patch_static.py"
]
CODES = {
  "test_active_page_routing.py": 41,
  "test_bridge_ping_status_compaction.py": 42,
  "test_bridge_server_hardened.py": 43,
  "test_bridge_server_sent_semantics.py": 44,
  "test_dashboard_new_session_launch.py": 45,
  "test_install_hardened_bridge_fast_deadman_static.py": 46,
  "test_nightshift_wsl_transport_static.py": 47,
  "test_patch_v045_task_dedupe_static.py": 48,
  "test_route_consumer_resilience.py": 49,
  "test_session_route_bootstrap.py": 50,
  "test_status_compaction_nested.py": 51,
  "test_userscript_delivery_dedupe_static.py": 52,
  "test_userscript_v046_guard_static.py": 53,
  "test_v04x_task_dedupe_patch_static.py": 54
}

loader = unittest.TestLoader()
for filename in FILES:
    suite = loader.discover(str(ROOT), pattern=filename)
    result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0, failfast=True).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(CODES[filename])
raise SystemExit(0)
