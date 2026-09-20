from pathlib import Path
import importlib.util
import sys


ROOT = Path.cwd()


def load_hourly_cycle():
    path = ROOT / "control/hourly/hourly_cycle.py"
    spec = importlib.util.spec_from_file_location(
        "hourly_cycle_under_test",
        path,
    )
    assert spec is not None
    assert spec.loader is not None

    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_real_loader_can_import_dataclass_orchestrator():
    hourly = load_hourly_cycle()

    mod = hourly.load(
        "agent_orchestrator_loader_regression",
        ROOT / "control/hourly/agent_orchestrator.py",
    )

    assert hasattr(mod, "Decision")
    assert mod.Decision.__module__ in sys.modules


def test_real_loader_can_import_all_new_control_modules():
    hourly = load_hourly_cycle()

    modules = {
        "packet_hydrator_loader_regression":
            ROOT / "control/hourly/packet_hydrator.py",
        "candidate_queue_loader_regression":
            ROOT / "control/hourly/candidate_queue.py",
    }

    for name, path in modules.items():
        mod = hourly.load(name, path)
        assert mod is not None
        assert name in sys.modules
