from pathlib import Path
import subprocess

root = Path.home() / "prediction_research_weather"
python = Path.home() / "prediction_research/.venv/bin/python"
job = root / "control/jobs/weather_away_a19b.py"

if not root.is_dir():
    raise SystemExit("WEATHER_WORKTREE_MISSING")
if not python.is_file():
    raise SystemExit("PREDICTION_VENV_PYTHON_MISSING")
if not job.is_file():
    raise SystemExit("WEATHER_AWAY_JOB_MISSING")

proc = subprocess.run(
    [str(python), str(job.relative_to(root))],
    cwd=root,
    text=True,
)
raise SystemExit(proc.returncode)
