from __future__ import annotations

import importlib.util
import io
import sys
import unittest
from pathlib import Path

ROOT = Path("control/tampermonkey_multichat")
PATH = ROOT / "test_userscript_v046_guard_static.py"

try:
    spec = importlib.util.spec_from_file_location("v046_guard_target", PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
except ModuleNotFoundError as exc:
    if getattr(exc, "name", None) == "pytest":
        raise SystemExit(67)
    raise SystemExit(68)
except Exception:
    raise SystemExit(68)

METHODS = ["test_advanced_version_and_task_memory_exist","test_page_anchor_and_recent_turn_fallback_exist","test_nonempty_composer_is_never_overwritten","test_task_level_dedupe_precedes_submission","test_retry_storm_guard_exists","test_confirmed_delivery_remembers_task_before_ack"]
CODES = {
  "test_advanced_version_and_task_memory_exist": 61,
  "test_page_anchor_and_recent_turn_fallback_exist": 62,
  "test_nonempty_composer_is_never_overwritten": 63,
  "test_task_level_dedupe_precedes_submission": 64,
  "test_retry_storm_guard_exists": 65,
  "test_confirmed_delivery_remembers_task_before_ack": 66
}

for method in METHODS:
    suite = unittest.TestSuite([mod.UserscriptV046GuardStaticTests(method)])
    result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(CODES[method])
raise SystemExit(0)
