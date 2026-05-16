import json
from typing import Any


def to_jsonable(value: Any) -> Any:
    return json.loads(json.dumps(value, default=str))
