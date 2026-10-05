from __future__ import annotations

import io
import json
import sys
import unittest

loader = unittest.TestLoader()
suite = loader.discover("tests/control_center", pattern="test_control_center.py")
stream = io.StringIO()
runner = unittest.TextTestRunner(stream=stream, verbosity=2)
result = runner.run(suite)

issues = []
for test, tb in list(result.failures) + list(result.errors):
    issues.append({
        "test": str(test),
        "traceback": tb,
    })

payload = {
    "tests_run": result.testsRun,
    "failures": len(result.failures),
    "errors": len(result.errors),
    "successful": result.wasSuccessful(),
    "first_issue_test": issues[0]["test"] if issues else None,
}
print("CONTROL_CENTER_E017_DIAG=" + json.dumps(payload, separators=(",", ":")), flush=True)
if issues:
    print("FIRST_TRACEBACK_BEGIN", flush=True)
    print(issues[0]["traceback"][-14000:], flush=True)
    print("FIRST_TRACEBACK_END", flush=True)
else:
    print("NO_TEST_FAILURE_REPRODUCED", flush=True)

sys.exit(0)
