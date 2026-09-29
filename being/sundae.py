"""Easter egg: say "ice cream" (in English) and the building shows the Sundai sundae — the
animated clip from the Green Building simulator's demo — as a quick ~2 s flash (GB_SUNDAE_SECS)
right as its reply lands, then it goes back to being its creature. Only for that exact word; never on boot.

Clip format (same as the simulator's): b'C', fps (1 byte), n frames (uint16 LE), then n frames
of 17x9 RGB bytes, row-major.
"""
from __future__ import annotations
import os
import re

import numpy as np

ROWS, COLS = 17, 9
PATH = os.path.join(os.path.dirname(__file__), "assets", "sundai-sundae.bin")
TRIGGER = re.compile(r"\bice[\s-]?creams?\b", re.I)
_CLIP = None


def mentioned(text: str) -> bool:
    return bool(TRIGGER.search(text or ""))


def load_clip():
    """(frames float[n,17,9,3] in 0..1, fps) or None; cached after the first read."""
    global _CLIP
    if _CLIP is not None:
        return _CLIP or None
    _CLIP = False
    try:
        with open(PATH, "rb") as fh:
            data = fh.read()
    except OSError:
        return None
    fsz = ROWS * COLS * 3
    if len(data) < 4 or data[0] != ord("C"):
        return None
    fps, n = data[1] or 30, data[2] | data[3] << 8
    if n <= 0 or len(data) < 4 + n * fsz:
        return None
    frames = np.frombuffer(data[4:4 + n * fsz], dtype=np.uint8).reshape(n, ROWS, COLS, 3)
    _CLIP = (frames.astype(float) / 255.0, fps)
    return _CLIP


def duration(clip) -> float:
    frames, fps = clip
    return len(frames) / float(fps)


def make_render(clip):
    """A render(buf, t) that plays the clip from its first frame, looping."""
    frames, fps = clip
    t0 = [None]

    def render(buf, t):
        if t0[0] is None:
            t0[0] = t
        buf[:] = frames[int((t - t0[0]) * fps) % len(frames)]
    return render
