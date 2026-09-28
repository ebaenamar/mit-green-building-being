"""Boot splash: when it (re)starts, the building first shows the Sundai sundae — the animated
logo clip from the Green Building simulator's demo (/demos/sundai-sundae.bin) — and only then
turns into its creature self.

Clip format (same as the simulator's): b'C', fps (1 byte), n frames (uint16 LE), then n frames
of 17x9 RGB bytes, row-major.
"""
from __future__ import annotations
import os
import time

import numpy as np

ROWS, COLS = 17, 9
DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "assets", "sundai-sundae.bin")
REMOTE_URL = "https://sundai.willsarg.com/demos/sundai-sundae.bin"


def load_clip(path: str = DEFAULT_PATH):
    """Return (frames float[n,17,9,3] in 0..1, fps) or None. Falls back to the simulator URL."""
    data = None
    try:
        with open(path, "rb") as fh:
            data = fh.read()
    except OSError:
        try:
            import urllib.request
            with urllib.request.urlopen(REMOTE_URL, timeout=10) as r:
                data = r.read()
        except Exception:
            return None
    fsz = ROWS * COLS * 3
    if not data or len(data) < 4 or data[0] != ord("C"):
        return None
    fps, n = data[1] or 30, data[2] | data[3] << 8
    if n <= 0 or len(data) < 4 + n * fsz:
        return None
    frames = np.frombuffer(data[4:4 + n * fsz], dtype=np.uint8).reshape(n, ROWS, COLS, 3)
    return frames.astype(float) / 255.0, fps


def make_render(clip):
    """A render(buf, t) that plays the clip from its first frame, looping."""
    frames, fps = clip
    t0 = [None]

    def render(buf, t):
        if t0[0] is None:
            t0[0] = t
        i = int((t - t0[0]) * fps) % len(frames)
        buf[:] = frames[i]
    return render
