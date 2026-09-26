"""CLI entry point for the local Prediction Control Room V0.

Input: command-line bind/repository options.
Output: starts the read-only local HTTP dashboard.
Non-goals: service installation, remote exposure, or project mutation.
"""

from .server import main

raise SystemExit(main())
