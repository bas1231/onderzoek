from pathlib import Path
from typing import Literal, Any

from pydantic import BaseModel, Field, field_validator, model_validator

from edge_hunter.build_gate import authorize_task


ALLOWED_EXECUTABLES = {
    "python",
    "python3",
    ".venv/bin/python",
}


class Task(BaseModel):
    task_id: str = Field(min_length=3, max_length=120)
    hypothesis_id: str = Field(min_length=1, max_length=120)

    task_class: Literal[
        "infrastructure",
        "research",
    ] = "research"

    operation: Literal[
        "health_check",
        "pytest",
        "python",
    ]

    working_directory: str = "."
    command: list[str]
    timeout_seconds: int = Field(default=300, ge=1, le=3600)
    live_trading: bool = False
    build_authorization: dict[str, Any] | None = None

    @field_validator("live_trading")
    @classmethod
    def trading_must_be_disabled(cls, value: bool) -> bool:
        if value:
            raise ValueError("live trading is forbidden")
        return value

    @field_validator("working_directory")
    @classmethod
    def safe_working_directory(cls, value: str) -> str:
        path = Path(value)

        if path.is_absolute():
            raise ValueError("absolute working directories are forbidden")

        if ".." in path.parts:
            raise ValueError("parent traversal is forbidden")

        return value

    @field_validator("command")
    @classmethod
    def basic_command_safety(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("empty command")

        if value[0] not in ALLOWED_EXECUTABLES:
            raise ValueError(
                f"executable not allowed: {value[0]}"
            )

        forbidden = {
            "sudo",
            "ssh",
            "scp",
            "curl",
            "wget",
            "rm",
            "dd",
            "kill",
            "killall",
            "exit",
        }

        for item in value:
            if item in forbidden:
                raise ValueError(
                    f"forbidden command element: {item}"
                )

        return value

    @model_validator(mode="after")
    def operation_command_match(self):
        command = self.command

        if self.operation == "health_check":
            if command != [
                ".venv/bin/python",
                "experiments/health_check.py",
            ]:
                raise ValueError(
                    "health_check command must use the canonical health script"
                )

        elif self.operation == "python":
            if len(command) < 2:
                raise ValueError("python operation requires a script")

            script = Path(command[1])

            if command[1].startswith("-"):
                raise ValueError(
                    "python -c / -m style execution is forbidden"
                )

            if script.is_absolute() or ".." in script.parts:
                raise ValueError("unsafe Python script path")

            allowed_prefixes = (
                "experiments/",
                "control/jobs/",
            )

            script_text = script.as_posix()

            if not script_text.startswith(allowed_prefixes):
                raise ValueError(
                    "Python scripts must live under experiments/ or control/jobs/"
                )

            if script.suffix != ".py":
                raise ValueError("Python task must execute a .py file")

        elif self.operation == "pytest":
            if len(command) < 3:
                raise ValueError("pytest command incomplete")

            if command[0] != ".venv/bin/python":
                raise ValueError(
                    "pytest must use project virtualenv python"
                )

            if command[1:3] != ["-m", "pytest"]:
                raise ValueError(
                    "pytest must run through python -m pytest"
                )

        authorization = authorize_task(self.model_dump())

        if not authorization["allowed"]:
            reasons = ",".join(authorization["reasons"])
            raise ValueError(
                "build authorization denied: " + reasons
            )

        return self
