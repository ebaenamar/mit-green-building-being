"""Transformation periods between recognizable emblems: the being does not cut between
symbols, it *becomes* the next. One emblem dissolves as the next assembles, with a
bright frontier where the change happens. Works with any renderer callable render(buf,t).
"""
from __future__ import annotations
import numpy as np

from .glyph import ROWS, COLS, _noise

_ORDER = np.array([[_noise(r * 3 + 1, c * 7 + 2, 9) for c in range(COLS)] for r in range(ROWS)])


class Expression:
    """Holds the current emblem (a callable render(buf,t)) and morphs toward a new one."""

    def __init__(self):
        self.cur = None
        self.tgt = None
        self.cur_id = None
        self.tgt_id = None
        self.p = 1.0
        self.dur = 1.2
        self._a = np.zeros((ROWS, COLS, 3))
        self._b = np.zeros((ROWS, COLS, 3))

    def set_render(self, fn, ident=None, dur=1.2):
        if self.cur is None:
            self.cur, self.cur_id, self.p, self.tgt = fn, ident, 1.0, None
            return
        if ident is not None and ident == self.cur_id and self.tgt is None:
            return                                   # already showing it
        self.tgt, self.tgt_id, self.p, self.dur = fn, ident, 0.0, max(0.2, dur)

    @property
    def transforming(self):
        return self.tgt is not None

    def update(self, dt):
        if self.tgt is not None:
            self.p += dt / self.dur
            if self.p >= 1.0:
                self.cur, self.cur_id, self.tgt, self.p = self.tgt, self.tgt_id, None, 1.0

    def render(self, buf, t, tint=None):
        if self.cur is None:
            buf[:] = 0.0
            return
        if self.tgt is None:
            self.cur(buf, t)
            return
        self.cur(self._a, t)
        self.tgt(self._b, t)
        p = self.p * self.p * (3 - 2 * self.p)       # smoothstep
        reveal = _ORDER < p
        frontier = np.abs(_ORDER - p) < 0.09
        buf[:] = np.where(reveal[..., None], self._b, self._a)
        spark = 0.6 + 0.4 * np.sin(t * 20)
        buf[frontier] = np.clip(buf[frontier] + spark, 0, 1)
