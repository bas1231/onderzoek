from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path


def main() -> None:
    private_key_path = os.environ.get("KALSHI_PRIVATE_KEY_PATH")
    result = {
        "api_key_id_present": bool(os.environ.get("KALSHI_API_KEY_ID")),
        "private_key_path_present": bool(private_key_path),
        "private_key_file_exists": bool(
            private_key_path and Path(private_key_path).is_file()
        ),
        "websockets_available": importlib.util.find_spec("websockets") is not None,
        "cryptography_available": importlib.util.find_spec("cryptography") is not None,
        "credential_values_printed": False,
        "live_trading": False,
        "paid_action": False,
        "wallet_action": False,
    }
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
