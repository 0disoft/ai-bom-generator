from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TextIO


def write_json_file(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_stable_json(payload), encoding="utf-8", newline="\n")


def write_json_stream(stream: TextIO, payload: Any) -> None:
    stream.write(_stable_json(payload))
    stream.write("\n")


def _stable_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
