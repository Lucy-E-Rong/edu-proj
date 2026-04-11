from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


REGISTRY_PATH = Path("data/adapters/registry.json")
ADAPTER_NAME_RE = re.compile(r"^[A-Za-z0-9_-]{2,64}$")


def validate_adapter_name(name: str) -> str:
    cleaned = name.strip()
    if not ADAPTER_NAME_RE.fullmatch(cleaned):
        raise ValueError("Adapter name must be 2-64 characters using letters, numbers, '_' or '-'.")
    return cleaned


def _read_user_registry() -> Dict[str, Dict[str, Any]]:
    if not REGISTRY_PATH.exists():
        return {}
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def _write_user_registry(registry: Dict[str, Dict[str, Any]]) -> None:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def builtin_adapters(config: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    profiles = config.get("runtime", {}).get("model_profiles", {})
    out: Dict[str, Dict[str, Any]] = {}
    for name, profile in profiles.items():
        out[name] = {
            "name": name,
            "type": name if name in {"base", "general", "teacher"} else "builtin",
            "adapter_path": profile.get("adapter_path"),
            "description": profile.get("description", ""),
            "status": "ready",
            "source": "config",
        }
    return out


def list_adapters(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    merged = builtin_adapters(config)
    for name, item in _read_user_registry().items():
        merged[name] = {"name": name, **item, "source": "registry"}
    return sorted(merged.values(), key=lambda item: item["name"])


def get_adapter(config: Dict[str, Any], name: str) -> Dict[str, Any] | None:
    cleaned = name.strip()
    builtins = builtin_adapters(config)
    if cleaned in builtins:
        return builtins[cleaned]
    item = _read_user_registry().get(cleaned)
    if item:
        return {"name": cleaned, **item, "source": "registry"}
    return None


def adapter_exists(config: Dict[str, Any], name: str) -> bool:
    return get_adapter(config, name) is not None


def register_adapter(
    name: str,
    adapter_path: str,
    source_files: List[str],
    description: str = "",
    status: str = "ready",
) -> Dict[str, Any]:
    registry = _read_user_registry()
    record = {
        "type": "teacher",
        "adapter_path": adapter_path,
        "description": description,
        "source_files": source_files,
        "status": status,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    registry[name] = record
    _write_user_registry(registry)
    return {"name": name, **record, "source": "registry"}
