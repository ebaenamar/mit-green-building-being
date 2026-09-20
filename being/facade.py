"""The whole-facade mood field: physical-AI legibility at 90 m.

Up close the being wears a face/emblem; from across campus nobody reads 9 px of detail —
they read COLOUR, BRIGHTNESS, RHYTHM and big motion across all 153 windows. This module
fills the entire 17x9 grid with a living mood field derived from emotion + drives + the
city, so the building itself is visibly alive and autonomous whether or not anyone chats:
it dims and withdraws when lonely or at 3am, warms and opens at golden hour, shimmers
restlessly before a storm, blooms when an urge to express breaks out.

render_wash() fills a buffer; the current face/emblem is composited on top of it.
"""
from __future__ import annotations
import math
import numpy as np

ROWS, COLS = 17, 9
_GRAD = np.linspace(0.70, 1.0, ROWS)[:, None]          # top a touch dimmer (it stands in sky)


def _clamp(x, lo=0.0, hi=1.0):
    return lo if x < lo else hi if x > hi else x


def _mood_rgb(v, a, cu):
    """A bold, few-hue mood colour. Cool indigo when low, warm gold when glad, agitated
    red when roused-and-unpleasant, a teal lean when curious."""
    cold = (0.10, 0.16, 0.42)      # low valence, calm  -> deep blue
    warm = (0.98, 0.60, 0.16)      # high valence       -> gold
    r = cold[0] + (warm[0] - cold[0]) * v
    g = cold[1] + (warm[1] - cold[1]) * v
    b = cold[2] + (warm[2] - cold[2]) * v
    if v < 0.45:                    # roused + unpleasant -> push toward agitated red
        k = _clamp((a - 0.45) * 1.6) * (0.45 - v) * 2
        r = r + (0.85 - r) * k
        g = g + (0.10 - g) * k
        b = b + (0.18 - b) * k
    if cu > 0.6:                    # curiosity -> a teal exploratory lean
        k = (cu - 0.6) * 0.6
        g = min(1.0, g + 0.25 * k)
        b = min(1.0, b + 0.15 * k)
    return r, g, b


def render_wash(buf, state, drives=None, city=None, t=0.0, event=None):
    """Fill buf (17x9x3 float) with the whole-facade mood field."""
    v = getattr(state, "valence", 0.6)
    a = getattr(state, "arousal", 0.5)
    cu = getattr(state, "curiosity", 0.5)
    sat = getattr(state, "saturation", 0.0)
    r, g, b = _mood_rgb(v, a, cu)

    bright = 0.28 + 0.5 * a + 0.15 * (v - 0.5)
    lonely = bored = 0.0
    if drives is not None:
        lonely = _clamp(getattr(drives, "social", 0.3) - 0.5) * 2
        bored = _clamp(getattr(drives, "stimulation", 0.3) - 0.55) * 2
        bright -= 0.22 * lonely                         # lonely -> withdraw, dim
    golden = night = unrest = 0.0
    if city is not None:
        try:
            _p, golden, night = city._phase()
            unrest = city.res.get("unrest", 0.0)
        except Exception:
            pass
    bright -= 0.30 * night                              # deep night -> dim, pulled inward
    bright += 0.16 * golden                             # golden hour -> warm bloom
    bright = _clamp(bright, 0.05, 1.0)

    breath = 0.84 + 0.16 * math.sin(t * 1.6)            # always-on breathing = baseline of alive
    field = np.ones((ROWS, COLS)) * bright * breath * _GRAD

    # restless shimmer: high arousal, overload, or a barometer about to turn (pre-storm)
    agit = _clamp(max(a - 0.6, 0) * 2 + 0.8 * unrest + 0.6 * sat)
    if agit > 0.02:
        ph = int(t * 11)
        noise = np.array([[((math.sin(rr * 12.9 + cc * 78.2 + ph * 37.7) * 43758.5) % 1.0)
                           for cc in range(COLS)] for rr in range(ROWS)])
        field += agit * 0.35 * (noise - 0.5)

    # travelling band = slow "pacing" when lonely/bored but calm (searching the night)
    pace = _clamp(0.6 * lonely + 0.5 * bored) * (1 - _clamp(a - 0.5) * 2)
    if pace > 0.05:
        pos = (t * (1.2 + 0.8 * a)) % (ROWS + 6) - 3
        band = np.exp(-((np.arange(ROWS) - pos) / 2.2) ** 2)[:, None]
        field += 0.30 * pace * band

    field = _apply_event(field, event, t)

    field = np.clip(field, 0.0, 1.2)
    if sat > 0.4:                                       # overload desaturates toward pale glare
        r = r + (1.0 - r) * (sat - 0.4) * 0.6
        g = g + (1.0 - g) * (sat - 0.4) * 0.6
        b = b + (1.0 - b) * (sat - 0.4) * 0.6
    buf[:, :, 0] = np.clip(r * field, 0, 1)
    buf[:, :, 1] = np.clip(g * field, 0, 1)
    buf[:, :, 2] = np.clip(b * field, 0, 1)


def _apply_event(field, event, t):
    """A transient, legible whole-facade gesture set by a drive/mood moment.
    event = (kind, t0, dur)."""
    if not event:
        return field
    kind, t0, dur = event
    p = (t - t0) / max(0.4, dur)
    if p < 0 or p > 1:
        return field
    env = math.sin(math.pi * _clamp(p))                 # rise then fall
    rows = np.arange(ROWS)[:, None]
    cols = np.arange(COLS)[None, :]
    if kind == "bloom":                                 # urge to express -> bright bloom from core
        d = np.sqrt(((rows - 8.5) / 6.0) ** 2 + ((cols - 4) / 4.0) ** 2)
        field = field + 0.7 * env * np.clip(1 - d, 0, 1)
    elif kind == "withdraw":                            # lonely -> dim and collapse inward
        d = np.sqrt(((rows - 8.5) / 6.0) ** 2 + ((cols - 4) / 4.0) ** 2)
        field = field * (1 - 0.45 * env) + 0.15 * env * np.clip(1 - d, 0, 1)
    elif kind == "ripple":                              # bored/self-stimulate -> a sweep of light
        pos = p * (ROWS + 4) - 2
        band = np.exp(-((rows - pos) / 1.6) ** 2)
        field = field + 0.5 * env * band
    elif kind == "perk":                                # someone's here -> quick brighten + lean
        field = field + 0.4 * env
    return field
