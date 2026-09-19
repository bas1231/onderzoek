from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator


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
    def safe_command(cls, value: list[str]) -> list[str]:
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
        }

        for item in value:
            if item in forbidden:
                raise ValueError(
                    f"forbidden command element: {item}"
                )

        return value
