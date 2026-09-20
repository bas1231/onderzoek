# Experiment lifecycle manifests

Tijdelijke experimentresources worden alleen automatisch opgeruimd
wanneer hun ownership expliciet in een manifest staat.

Voorbeeld:

{
  "experiment_id": "EXAMPLE",
  "state": "RUNNING",
  "cleanup": {
    "enabled": true,
    "systemd_user_units": [
      "prediction-research-exp-example.service"
    ],
    "delete_paths": [
      "~/.local/state/prediction-research/experiments/EXAMPLE/runtime"
    ]
  }
}

Cleanup wordt uitsluitend uitgevoerd bij:
COMPLETED, FAILED, ABORTED, FALSIFIED of TESTED_NEGATIVE.

Evidence, resultaten, logs, knowledge en Git-data zijn geen
automatische cleanup-targets.

Permanente control-plane units zijn beschermd.
