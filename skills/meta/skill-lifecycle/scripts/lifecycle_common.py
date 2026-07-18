"""Shared persistence helpers for skill lifecycle tools."""

import json
import os
import tempfile
from pathlib import Path


def read_json(path):
    """Read a UTF-8 JSON object from path."""
    with Path(path).open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object in {path}")
    return value


def deterministic_json(value):
    """Return the canonical human-readable JSON representation."""
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def atomic_write_json(path, value):
    """Atomically replace path using a temporary file in the same directory."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_name = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_name = handle.name
            handle.write(deterministic_json(value))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, destination)
        temporary_name = None
    finally:
        if temporary_name is not None:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass
