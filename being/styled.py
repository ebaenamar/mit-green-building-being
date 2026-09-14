"""Creative style engine: take a recognizable emblem (fire, boat, hand, sun...) and
render a FRESH, colorful variation every time — recoloring it, shifting its palette,
and adding ornaments (sparkles, halo, embers, rain, petals) — so the being's body looks
like the rich emblems we drew, yet never repeats and always reflects how it feels now.
"""
from __future__ import annotations
import colorsys
import numpy as np

from . import emblem_registry
from .glyph import _set, ROWS, COLS

# a bright, colorful accent rotation so consecutive expressions never look the same
_ACCENTS = ["#ff3b6b", "#ff9e2c", "#ffe14d", "#4dff9e", "#2cd7ff", "#7c5cff",
            "#ff5ce0", "#00e5c7", "#ff6a3d", "#a0ff3d"]
_ORNAMENTS = ["sparkle", "halo", "embers", "rain", "petals", "orbit", "none"]


def style_for(state, i: int) -> dict:
    """Compose a non-repeating style from feeling + a rotation index i. Each i gives a
    visibly fresh look (new hue + a different fitting ornament), same emotion."""
    rot = (i * 0.137) % 1.0                       # golden-ish rotation -> always different
    warm = -0.04 if state.valence > 0.5 else 0.06
    dom = (state.dominant_emotion or "").lower()
    # a few ornaments that fit each mood; rotate through them so restyles look new
    opts = {"excited": ["embers", "sparkle", "orbit"], "restless": ["embers", "orbit", "sparkle"],
            "alert": ["embers", "sparkle"], "curious": ["sparkle", "orbit", "halo"],
            "fascinated": ["sparkle", "halo"], "surprised": ["sparkle", "embers"],
            "serene": ["halo", "petals", "sparkle"], "contemplative": ["halo", "petals"],
            "calm": ["halo", "petals"], "melancholic": ["rain", "halo"], "lonely": ["rain", "halo"],
            "affectionate": ["petals", "sparkle", "halo"], "playful": ["orbit", "sparkle", "embers"],
            "overwhelmed": ["orbit", "embers", "rain"]}.get(dom, _ORNAMENTS)
    orn = opts[i % len(opts)]
    # scale/deform the shape itself: bigger & bolder when aroused, smaller when withdrawn,
    # plus a per-regeneration wobble so the geometry actually changes, not just the color.
    scale = 0.8 + 0.5 * state.arousal + 0.12 * ((i % 3) - 1)
    return {
        "hue_shift": round((warm + rot) % 1.0, 3),
        "sat": round(1.0 + 0.25 * state.arousal, 3),
        "bright": round(0.75 + 0.4 * state.valence + 0.2 * state.arousal, 3),
        "accent": _ACCENTS[i % len(_ACCENTS)],
        "ornament": orn,
        "energy": round(0.3 + 0.7 * state.arousal, 3),
        "scale": round(max(0.65, min(1.35, scale)), 3),
    }


def _recolor(buf, hue, sat, bright):
    for r in range(ROWS):
        for c in range(COLS):
            px = buf[r, c]
            if px[0] + px[1] + px[2] <= 0.02:
                continue
            h, s, v = colorsys.rgb_to_hsv(px[0], px[1], px[2])
            h = (h + hue) % 1.0
            s = min(1.0, s * sat)
            v = min(1.0, v * bright)
            buf[r, c] = colorsys.hsv_to_rgb(h, s, v)


def _hex(s):
    s = s.lstrip("#")
    return (int(s[0:2], 16) / 255, int(s[2:4], 16) / 255, int(s[4:6], 16) / 255)


def _ornament(buf, style, t):
    kind = style.get("ornament", "none")
    col = _hex(style.get("accent", "#ffffff"))
    e = style.get("energy", 0.5)
    if kind == "sparkle":
        for k in range(4):
            r = int((2 + 3 * k + t * 2) % ROWS)
            c = int((1 + 2 * k) % COLS)
            _set(buf, r, c, col, 0.5 + 0.5 * np.sin(t * 6 + k))
    elif kind == "halo":
        cx, cy, rad = 4, 8.5, 6.0
        for a in range(0, 360, 30):
            rr = cy - np.sin(np.radians(a)) * rad
            cc = cx + np.cos(np.radians(a)) * rad
            _set(buf, int(round(rr)), int(round(cc)), col, 0.35 + 0.25 * np.sin(t * 2 + a))
    elif kind == "embers":
        for k in range(int(3 + 5 * e)):
            r = int((ROWS - 1 - (t * (4 + 4 * e) + k * 3)) % ROWS)
            c = int((4 + 3 * np.sin(t + k)) % COLS)
            _set(buf, r, c, col, 0.7)
    elif kind == "rain":
        for k in range(int(4 + 6 * e)):
            r = int((t * 8 + k * 2) % ROWS)
            c = int((k * 5 + 1) % COLS)
            _set(buf, r, c, col, 0.5)
    elif kind == "petals" or kind == "orbit":
        n = 5 if kind == "petals" else 6
        for k in range(n):
            a = t * (1.5 if kind == "orbit" else 0.8) + k * 2 * np.pi / n
            rr = 8.5 - np.sin(a) * 5.5
            cc = 4 + np.cos(a) * 4.0
            _set(buf, int(round(rr)), int(round(cc)), col, 0.6)


def _rescale(src, dst, scale):
    """Zoom/shrink src into dst around the centre (nearest-neighbour) — reshapes the body."""
    cy, cx = (ROWS - 1) / 2.0, (COLS - 1) / 2.0
    dst[:] = 0.0
    for r in range(ROWS):
        ir = int(round(cy + (r - cy) / scale))
        if 0 <= ir < ROWS:
            for c in range(COLS):
                ic = int(round(cx + (c - cx) / scale))
                if 0 <= ic < COLS:
                    dst[r, c] = src[ir, ic]


def make_styled(name: str, style: dict):
    """Return a render(buf, t) that draws emblem `name` in this fresh style (colour,
    ornament AND scale/deformation), so the shape itself is modified, not just tinted."""
    base = emblem_registry.get(name) or emblem_registry.get("sun")
    hue = float(style.get("hue_shift", 0.0))
    sat = float(style.get("sat", 1.0))
    bright = float(style.get("bright", 1.0))
    scale = float(style.get("scale", 1.0))
    tmp = np.zeros((ROWS, COLS, 3))

    def render(buf, t):
        tmp[:] = 0.0
        base(tmp, t)
        _recolor(tmp, hue, sat, bright)
        if abs(scale - 1.0) < 0.03:
            buf[:] = tmp
        else:
            _rescale(tmp, buf, scale)
        _ornament(buf, style, t)
    return render
