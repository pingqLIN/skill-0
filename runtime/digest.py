from __future__ import annotations

import hashlib
import hmac
import json


def canonical_digest(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def keyed_digest(value: object, *, key: str) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return (
        "hmac-sha256:"
        + hmac.new(key.encode("utf-8"), encoded, hashlib.sha256).hexdigest()
    )
