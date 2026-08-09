from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
import hashlib
import json


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def stable_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(payload).hexdigest()
