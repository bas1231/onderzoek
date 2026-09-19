from pathlib import Path
import json

ROOT = Path.cwd()
REGISTRY = ROOT / "knowledge/sources/registry.json"

def load_registry():
    data = json.loads(REGISTRY.read_text())
    seen = set()
    for source in data.get("sources", []):
        sid = source.get("id")
        if not sid: raise RuntimeError("missing source id")
        if sid in seen: raise RuntimeError("duplicate source id: " + sid)
        seen.add(sid)
        if source.get("cost_class") != "free_public": raise RuntimeError("non-free source blocked: " + sid)
    return data

if __name__ == "__main__":
    data = load_registry()
    print(json.dumps({"ok": True, "sources": len(data["sources"])}, sort_keys=True))
