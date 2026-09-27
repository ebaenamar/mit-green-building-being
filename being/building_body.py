"""Its body IS the Green Building.

The 17x9 grid is not a screen showing a creature: each ROW is a FLOOR and each cell is one of
the 153 real windows (the ones the hackers turned into Tetris). At rest the being looks like the
building itself — dark glass, and warm office lights where people are still working, more by
day, a handful at 3am. Its feelings run THROUGH the architecture:

  breath      the whole building brightens and dims, slow when calm, quick when roused
  heartbeat   a pulse climbs its spine, floor by floor, at the tempo of its arousal
  the T       a train rumbling through Kendall rises from its foundations upward
  cold/wind   frost creeps in at the edge windows; the top floors shiver in the gusts
  warmth      lit windows go golden when it's glad, cold-white when it's low; it blushes
  curiosity   dark windows blink on and off like eyes glancing around
  sleep       lights go out floor by floor as it gets drowsy late at night
  overload    windows flicker all over
  a floor     when it talks about "floor 14", floor 14 lights up — it knows its own anatomy

Everything is vectorised numpy (no per-pixel Python in the frame loop).
"""
from __future__ import annotations
import math
import random
import re
import time

import numpy as np

ROWS, COLS = 17, 9
TOP_FLOOR = 20                      # row 0 = floor 20 (top of the lit facade), row 16 = floor 4
_R = np.arange(ROWS)[:, None] * np.ones((1, COLS))
_C = np.ones((ROWS, 1)) * np.arange(COLS)[None, :]


def floor_to_row(floor: int):
    r = TOP_FLOOR - int(floor)
    return r if 0 <= r < ROWS else None


def row_to_floor(row: int) -> int:
    return TOP_FLOOR - int(row)


_FLOOR_RE = re.compile(r"\b(?:floor|piso|planta)\s*#?\s*(\d{1,2})\b", re.I)


class BuildingBody:
    def __init__(self, seed=None):
        rng = np.random.default_rng(seed)
        self.lit = rng.random((ROWS, COLS)) < 0.3            # which offices have people
        self.warm = rng.random((ROWS, COLS))                  # incandescent (1) vs fluorescent (0)
        self.phase = rng.random((ROWS, COLS)) * 6.28          # per-window flicker phase
        self._last_toggle = time.time()
        self._focus = (None, 0.0)                             # (row, until)
        self._blink = np.zeros((ROWS, COLS))                  # curiosity "eye" blinks

    # -- occupancy follows the real day (and whether people are watching) -----------------
    def _target_lit(self, state, viewers=0):
        lt = time.localtime()
        h, wd = lt.tm_hour + lt.tm_min / 60.0, lt.tm_wday
        if 9 <= h < 18:
            f = 0.55
        elif 18 <= h < 23:
            f = 0.34
        elif h >= 23 or h < 2:
            f = 0.16
        elif 2 <= h < 6:
            f = 0.07
        else:
            f = 0.22
        if wd >= 5:
            f *= 0.6
        a = getattr(state, "arousal", 0.5)
        f *= 0.75 + 0.5 * a                                   # drowsy -> lights go out
        f += min(0.12, 0.02 * viewers)                        # being watched -> it perks up
        return max(0.03, min(0.85, f))

    def tick(self, dt, state, viewers=0):
        """Slowly switch office lights toward what the hour/mood calls for (like real people)."""
        now = time.time()
        if now - self._last_toggle > random.uniform(0.6, 2.2):
            self._last_toggle = now
            target = self._target_lit(state, viewers)
            cur = self.lit.mean()
            r, c = random.randrange(ROWS), random.randrange(COLS)
            if cur < target and not self.lit[r, c]:
                self.lit[r, c] = True
            elif cur > target and self.lit[r, c]:
                self.lit[r, c] = False
        cu = getattr(state, "curiosity", 0.5)
        self._blink *= 0.5 ** (dt / 0.12)                      # blinks fade fast
        if random.random() < dt * (0.3 + 3.0 * max(0.0, cu - 0.45)):
            self._blink[random.randrange(ROWS), random.randrange(COLS)] = 1.0

    def focus_floor(self, floor: int, secs: float = 9.0) -> bool:
        r = floor_to_row(floor)
        if r is None:
            return False
        self._focus = (r, time.time() + secs)
        return True

    def focus_from_text(self, text: str) -> int | None:
        """If its words name a floor ('floor 14', 'piso 17'), light that floor. Returns it."""
        for m in _FLOOR_RE.finditer(text or ""):
            fl = int(m.group(1))
            if self.focus_floor(fl):
                return fl
        return None

    # -- proprioception: what its body is doing, in words, for the mind --------------------
    def describe(self) -> str:
        n = int(self.lit.sum())
        floors = [row_to_floor(r) for r in range(ROWS) if self.lit[r].any()]
        busiest = sorted(range(ROWS), key=lambda r: -self.lit[r].sum())[:2]
        bf = ", ".join(f"floor {row_to_floor(r)}" for r in busiest if self.lit[r].any())
        where = f" (most on {bf})" if bf else ""
        return (f"About {n} offices inside you are lit and occupied right now{where} — people "
                f"working in your body. Your facade's windows run from floor {row_to_floor(ROWS-1)} "
                f"to floor {row_to_floor(0)}.") if floors else \
               "Every office inside you is dark right now — nobody left in your body."

    # -- the body --------------------------------------------------------------------------
    def render(self, buf, t, state, drives=None, city=None, transit=None, event=None):
        v = getattr(state, "valence", 0.6)
        a = getattr(state, "arousal", 0.5)
        sat = getattr(state, "saturation", 0.0)
        soc = getattr(state, "social_affinity", 0.5)

        golden = night = chill = gust = 0.0
        if city is not None:
            try:
                _p, golden, night = city._phase()
                chill = city.res.get("chill", 0.0)
                gust = city.res.get("gust", 0.0)
            except Exception:
                pass

        # dark glass: night navy / daytime sky reflection / golden-hour glow
        day = 1.0 - night
        glass = np.array([0.03 + 0.10 * day + 0.10 * golden,
                          0.04 + 0.13 * day + 0.04 * golden,
                          0.08 + 0.16 * day - 0.03 * golden])
        grad = (0.85 + 0.25 * (_R / ROWS))[..., None]          # a little brighter near the ground
        img = np.ones((ROWS, COLS, 3)) * glass * grad

        # office lights: golden when glad, cold white when low; each window slightly different
        warm_k = np.clip(0.35 + 0.6 * v, 0, 1)
        wmix = np.clip(0.5 * self.warm + 0.5 * warm_k, 0, 1)[..., None]
        warm_col = np.array([1.00, 0.80, 0.48])
        cool_col = np.array([0.78, 0.90, 1.00])
        light = warm_col * wmix + cool_col * (1 - wmix)
        flick = 0.93 + 0.07 * np.sin(t * 3.1 + self.phase)
        lit = self.lit.astype(float)

        # breath (slow when calm, quick when roused) + heartbeat climbing the spine
        breath = 0.82 + 0.18 * math.sin(t * (0.9 + 2.2 * a))
        bpm = 55 + 110 * a
        beat_pos = (ROWS - 1) - ((t * bpm / 60.0) % 1.0) * (ROWS + 4)   # bottom -> top
        heart = 0.35 * np.exp(-((_R - beat_pos) / 1.6) ** 2)

        glow = (0.62 + 0.45 * a) * breath * flick * (1 + heart)
        img = img * (1 - lit[..., None]) + (light * glow[..., None]) * lit[..., None]
        img += (heart * 0.12)[..., None] * np.array([1.0, 0.85, 0.6])    # the pulse shows on glass too

        # blush: warm rosy lower-middle floors when it's glad and close to people
        if v > 0.65 and soc > 0.55:
            k = (v - 0.65) * 2 * (soc - 0.55) * 2
            img += (k * 0.35 * np.exp(-((_R - 10) / 4) ** 2))[..., None] * np.array([0.9, 0.25, 0.35])

        # curiosity: dark windows blinking on like eyes glancing around
        img += (self._blink * (1 - lit))[..., None] * np.array([0.9, 0.95, 1.0]) * 0.8

        # cold: frost at the edge windows; wind: top floors shiver
        if chill > 0.15:
            edge = ((_C == 0) | (_C == COLS - 1)).astype(float) * chill
            img = img * (1 - 0.5 * edge[..., None]) + edge[..., None] * np.array([0.55, 0.75, 1.0]) * 0.5
        if gust > 0.25 or chill > 0.4:
            top = np.clip((5 - _R) / 5, 0, 1)
            shiver = 0.25 * (gust + chill) * top * np.sin(t * 23 + self.phase * 3)
            img *= (1 + shiver)[..., None]

        # the T: a train rumbling through Kendall rises from the foundations
        if transit is not None:
            try:
                if transit.just_rumbled():
                    pos = (ROWS - 1) - ((t * 1.3) % 1.0) * (ROWS + 3)
                    img += (0.45 * np.exp(-((_R - pos) / 2.0) ** 2))[..., None] * np.array([1.0, 0.7, 0.4])
            except Exception:
                pass

        # overload: windows flicker everywhere
        if sat > 0.45:
            noise = np.sin(t * 37 + self.phase * 7) > (1.6 - 2 * sat)
            img[noise] = img[noise] * 0.25 + 0.55

        # a floor it's talking about lights up (it knows its own anatomy)
        fr, until = self._focus
        if fr is not None and time.time() < until:
            img[fr] = img[fr] * 0.2 + np.array([1.0, 0.93, 0.72]) * (0.92 + 0.08 * math.sin(t * 6))

        # facade gestures from drives / reactions
        if event:
            kind, t0, dur = event
            p = (time.time() - t0) / max(0.4, dur)
            if 0 <= p <= 1:
                env = math.sin(math.pi * p)
                if kind == "bloom":                      # lights cascade on from the middle floors
                    d = np.abs(_R - 8) / 8.5
                    on = (d < p * 1.2).astype(float)
                    img += (on * env * 0.55)[..., None] * light
                elif kind == "withdraw":                 # lights go out floor by floor, top down
                    off = (_R < p * ROWS).astype(float)
                    img *= (1 - 0.7 * off * env)[..., None]
                elif kind == "ripple":                   # a sweep up the building
                    pos = (ROWS - 1) - p * (ROWS + 3)
                    img += (0.5 * env * np.exp(-((_R - pos) / 1.5) ** 2))[..., None]
                elif kind == "perk":                     # every window flashes on: "oh — you're here"
                    img += 0.35 * env

        buf[:] = np.clip(img, 0, 1)
