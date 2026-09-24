"""Read-only observability dashboard for the local Prediction Research-OS.

Input: an existing repository/runtime tree.
Output: safe structured snapshots for a local browser UI.
Non-goals: trading, task execution, mutation, credentials, or external polling.
"""

from .model import build_snapshot

__all__ = ["build_snapshot"]
