import hashlib
import json
from typing import Any


def external_content_hash(source: str, payload: dict[str, Any]) -> str:
    stable = {
        "source": source,
        "id": payload.get("id") or payload.get("node_id") or payload.get("full_name"),
        "full_name": payload.get("full_name"),
        "updated_at": payload.get("updated_at"),
    }
    if not stable["id"]:
        stable["payload"] = payload
    encoded = json.dumps(stable, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
