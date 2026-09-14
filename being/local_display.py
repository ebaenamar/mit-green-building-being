"""A terminal preview that mimics the building's viewer, so you can watch the being
without an instance. Implements the same Display interface (send/makeframe) as the
real building and the WebDisplay, so the being code is identical either way.
"""
from __future__ import annotations
import sys

from gbsim.display import Display, Frame


class LocalDisplay(Display):
    def __init__(self, status_fn=None):
        self._status_fn = status_fn
        self._primed = False

    def makeframe(self):
        return Frame()

    def send(self, frame):
        rows, cols = frame.nrows(), frame.ncols()
        out = ["\x1b[H"]  # cursor home; each frame overwrites the last in place
        out.append("\x1b[2m  MIT Green Building — local viewer (Ctrl-C to leave)\x1b[0m\x1b[K\n")
        for r in range(rows):
            line = []
            for c in range(cols):
                col = frame[r][c]
                line.append(f"\x1b[48;2;{col.r};{col.g};{col.b}m  ")
            out.append("  " + "".join(line) + "\x1b[0m\x1b[K\n")
        if self._status_fn:
            out.append("\x1b[0m\x1b[K\n")
            out.append("  " + self._status_fn()[:78] + "\x1b[K\n")
            out.append("\x1b[K")
        if not self._primed:
            sys.stdout.write("\x1b[2J")  # clear once on first frame
            self._primed = True
        sys.stdout.write("".join(out))
        sys.stdout.flush()

    def flush(self, timeout=None):
        return True

    def close(self):
        sys.stdout.write("\x1b[0m\n")
        sys.stdout.flush()
