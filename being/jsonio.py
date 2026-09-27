"""Crash-safe JSON persistence: write to a temp file, then atomically replace the target.
A process killed mid-write (Render redeploys do that) never leaves a corrupt file behind —
the being wakes up with its last complete memory instead of amnesia."""
from __future__ import annotations
import json
import os


def atomic_write(path: str, obj, indent=None) -> bool:
    if not path:
        return False
    try:
        d = os.path.dirname(path)
        if d:
            os.makedirs(d, exist_ok=True)
        tmp = f"{path}.tmp"
        with open(tmp, "w") as fh:
            json.dump(obj, fh, indent=indent)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
        return True
    except OSError as e:
        print(f"persist: could not write {path}: {e}")
        return False
