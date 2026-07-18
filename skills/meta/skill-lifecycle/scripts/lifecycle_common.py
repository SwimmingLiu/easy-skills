"""Shared persistence helpers for skill lifecycle tools."""

import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

try:
    import fcntl
except ImportError:  # pragma: no cover - exercised only on non-POSIX hosts
    fcntl = None


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


def sibling_lock_path(path):
    destination = Path(path)
    return destination.with_name(f".{destination.name}.lock")


@contextmanager
def lifecycle_lock(path):
    """Hold an exclusive interprocess lock for one lifecycle destination."""
    if fcntl is None:
        raise OSError("lifecycle locking requires POSIX fcntl.flock on this platform")
    lock_path = sibling_lock_path(path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    if lock_path.is_symlink():
        raise OSError(f"refusing symlink lifecycle lock path: {lock_path}")
    with lock_path.open("a+") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def atomic_write_json(path, value):
    """Atomically replace path using a temporary file in the same directory."""
    destination = Path(path)
    if destination.is_symlink():
        raise OSError(f"refusing symlink lifecycle path: {destination}")
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
        if destination.is_symlink():
            raise OSError(f"refusing symlink lifecycle path: {destination}")
        os.replace(temporary_name, destination)
        temporary_name = None
        if os.name == "posix":
            directory_descriptor = os.open(destination.parent, os.O_RDONLY)
            try:
                os.fsync(directory_descriptor)
            finally:
                os.close(directory_descriptor)
    finally:
        if temporary_name is not None:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass
