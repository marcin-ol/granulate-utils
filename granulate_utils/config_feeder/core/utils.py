import json
from hashlib import blake2b
from typing import Any, Dict, List, Union

SENSITIVE_KEYS = ("password", "secret", "keytab", "principal")
MASK = "*****"


def get_config_hash(s: Union[str, Dict[str, Any], List[Any]], is_sorted: bool = False) -> str:
    if isinstance(s, str):
        s = s if is_sorted else json.dumps(json.loads(s), sort_keys=True)
    else:
        s = json.dumps(s, sort_keys=True)
    h = blake2b(digest_size=10)
    h.update(s.encode("utf-8"))
    return h.hexdigest()


def mask_sensitive_value(key: str, value: Any) -> Any:
    """
    Mask sensitive info
    """
    key = key.lower()
    return MASK if any(k in key for k in SENSITIVE_KEYS) else value
