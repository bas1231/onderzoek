from __future__ import annotations

import json
import time
from pathlib import Path

from parallel_build_coordination import (
    Coordinator as BaseCoordinator,
    DEFAULT_TTL_SECONDS,
    INTEGRATION_TTL_SECONDS,
    _git_text,
    build_parser,
)


class Coordinator(BaseCoordinator):
    """Coordinator whose runtime registry is shared by all worktrees of one repo."""

    def __init__(self, root: Path, ttl_seconds: int = DEFAULT_TTL_SECONDS):
        self.root = root.resolve()
        common_raw = _git_text(self.root, "rev-parse", "--git-common-dir")
        common_dir = Path(common_raw)
        if not common_dir.is_absolute():
            common_dir = (self.root / common_dir).resolve()
        self.git_common_dir = common_dir.resolve()
        self.runtime = self.git_common_dir / "prediction-build-coordination"
        self.sessions = self.runtime / "sessions"
        self.registry_lock_path = self.runtime / "registry.lock"
        self.integration_owner_path = self.runtime / "integration_owner.json"
        self.ttl_seconds = ttl_seconds
        self.sessions.mkdir(parents=True, exist_ok=True)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    coord = Coordinator(Path(args.root))
    if args.command == "start":
        result = coord.start(
            args.session_id,
            args.task_id,
            args.path,
            mutating=not args.read_only,
            ttl=args.ttl,
        )
    elif args.command == "status":
        sessions = coord.active_sessions()
        if args.session_id:
            sessions = [item for item in sessions if item.get("session_id") == args.session_id]
        result = {
            "ok": True,
            "status": "OK",
            "runtime": str(coord.runtime),
            "sessions": sessions,
        }
    elif args.command == "heartbeat":
        result = coord.heartbeat(args.session_id, args.ttl)
    elif args.command == "finish":
        result = coord.finish(args.session_id)
    elif args.command == "acquire-integration":
        result = coord.acquire_integration(args.session_id)
    elif args.command == "release-integration":
        result = coord.release_integration(args.session_id)
    elif args.command == "premerge":
        result = coord.premerge(args.session_id)
    elif args.command == "mark-validated":
        result = coord.mark_validated(args.session_id, args.main_sha)
    elif args.command == "publish-check":
        result = coord.publish_check(args.session_id)
    else:
        raise AssertionError(args.command)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
