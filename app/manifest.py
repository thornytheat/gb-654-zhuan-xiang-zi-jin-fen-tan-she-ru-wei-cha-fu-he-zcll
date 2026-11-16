from hashlib import sha256
import json

def canonical_digest(value) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(raw.encode("utf-8")).hexdigest()

def run_id(value) -> str:
    return "run-" + canonical_digest(value)[:12]
