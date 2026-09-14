"""A tiny symbol DSL so the being (or the AI) can *invent* emblems, not just pick them.

A glyph is data: a background plus a list of primitive layers, each with an optional
animation. render_glyph() draws it into a 17x9 float buffer at time t. Because glyphs
are plain dicts/JSON, the LLM can compose brand-new symbols live from an interaction,
and morph.py can tween smoothly between any two of them.

Primitive types: disc, ring, crescent, line, tri, rect, rays, flame, particles, grid.
Each may carry an "anim": pulse | flicker | spin | sway | twinkle | rise | none.
Colors are "#rrggbb" or [r,g,b] (0-255). Coords are grid cells (col x, row y),
center default (4, 8).
"""
from __future__ import annotations
import math

ROWS, COLS = 17, 9


def _col(v):
    if isinstance(v, str):
        s = v.lstrip("#")
        return (int(s[0:2], 16)/255, int(s[2:4], 16)/255, int(s[4:6], 16)/255)
    return (v[0]/255, v[1]/255, v[2]/255)


def _lerp3(a, b, t):
    return (a[0]+(b[0]-a[0])*t, a[1]+(b[1]-a[1])*t, a[2]+(b[2]-a[2])*t)


def _set(buf, r, c, col, a=1.0):
    if 0 <= r < ROWS and 0 <= c < COLS and a > 0:
        ia = 1-a
        buf[r, c, 0] = buf[r, c, 0]*ia + col[0]*a
        buf[r, c, 1] = buf[r, c, 1]*ia + col[1]*a
        buf[r, c, 2] = buf[r, c, 2]*ia + col[2]*a


def _noise(x, y, s=0):
    v = math.sin(x*12.9898 + y*78.233 + s*37.719) * 43758.5453
    return v - math.floor(v)


def _anim_offset(p, t):
    """Return (dx, dy, scale, alpha) modifiers from a primitive's anim spec."""
    kind = p.get("anim", "none")
    sp = p.get("anim_speed", 1.0)
    amt = p.get("anim_amt", 1.0)
    if kind == "pulse":
        return 0, 0, 1 + 0.12*amt*math.sin(t*3*sp), 1
    if kind == "sway":
        return amt*math.sin(t*2*sp), 0, 1, 1
    if kind == "rise":
        return 0, -amt*((t*sp) % 3), 1, 1
    if kind == "twinkle":
        return 0, 0, 1, 0.4 + 0.6*(math.sin(t*4*sp)*0.5+0.5)
    if kind == "flicker":
        return 0, 0, 1, 0.7 + 0.3*_noise(int(t*12*sp), 5),
    return 0, 0, 1, 1


def _draw_disc(buf, p, t, tint):
    dx, dy, sc, al = _anim_offset(p, t)
    cx, cy = p.get("cx", 4)+dx, p.get("cy", 8)+dy
    r = p.get("r", 3)*sc
    col = _tint(_col(p.get("color", "#ffffff")), tint)
    edge = _col(p["edge"]) if "edge" in p else None
    for R in range(ROWS):
        for C in range(COLS):
            d = math.hypot(C-cx, R-cy)
            if d <= r:
                c = _lerp3(col, _tint(edge, tint), d/r) if edge else col
                _set(buf, R, C, c, al)


def _draw_ring(buf, p, t, tint):
    dx, dy, sc, al = _anim_offset(p, t)
    cx, cy, r = p.get("cx", 4)+dx, p.get("cy", 8)+dy, p.get("r", 3)*sc
    th = p.get("thickness", 1.0)
    col = _tint(_col(p.get("color", "#ffffff")), tint)
    for R in range(ROWS):
        for C in range(COLS):
            if abs(math.hypot(C-cx, R-cy) - r) <= th*0.5:
                _set(buf, R, C, col, al)


def _draw_crescent(buf, p, t, tint):
    dx, dy, sc, al = _anim_offset(p, t)
    cx, cy, r = p.get("cx", 4)+dx, p.get("cy", 8)+dy, p.get("r", 3.5)*sc
    off = p.get("offset", 2.2)
    col = _tint(_col(p.get("color", "#eaf0ff")), tint)
    for R in range(ROWS):
        for C in range(COLS):
            if math.hypot(C-cx, R-cy) <= r and math.hypot(C-(cx+off), R-cy) > r-0.2:
                _set(buf, R, C, col, al)


def _draw_line(buf, p, t, tint):
    dx, dy, sc, al = _anim_offset(p, t)
    x1, y1 = p.get("x1", 4)+dx, p.get("y1", 2)+dy
    x2, y2 = p.get("x2", 4)+dx, p.get("y2", 14)+dy
    col = _tint(_col(p.get("color", "#ffffff")), tint)
    n = int(max(abs(x2-x1), abs(y2-y1))*2)+1
    for i in range(n+1):
        f = i/max(1, n)
        _set(buf, int(round(y1+(y2-y1)*f)), int(round(x1+(x2-x1)*f)), col, al)


def _draw_tri(buf, p, t, tint):
    dx, dy, sc, al = _anim_offset(p, t)
    raw = p.get("pts") or p.get("points")
    if not (isinstance(raw, (list, tuple)) and len(raw) >= 3):
        return
    pts = [(x+dx, y+dy) for x, y in raw[:3]]
    col = _tint(_col(p.get("color", "#ffffff")), tint)
    (ax, ay), (bx, by), (cx, cy) = pts

    def area(x1, y1, x2, y2, x3, y3):
        return abs((x2-x1)*(y3-y1)-(x3-x1)*(y2-y1))/2
    A = area(ax, ay, bx, by, cx, cy) or 1e-6
    for R in range(ROWS):
        for C in range(COLS):
            a1 = area(C, R, bx, by, cx, cy)
            a2 = area(ax, ay, C, R, cx, cy)
            a3 = area(ax, ay, bx, by, C, R)
            if a1+a2+a3 <= A+0.6:
                _set(buf, R, C, col, al)


def _draw_rect(buf, p, t, tint):
    dx, dy, sc, al = _anim_offset(p, t)
    x, y, w, h = p.get("x", 3)+dx, p.get("y", 6)+dy, p.get("w", 3), p.get("h", 4)
    col = _tint(_col(p.get("color", "#ffffff")), tint)
    for R in range(int(round(y)), int(round(y+h))):
        for C in range(int(round(x)), int(round(x+w))):
            _set(buf, R, C, col, al)


def _draw_rays(buf, p, t, tint):
    cx, cy = p.get("cx", 4), p.get("cy", 8)
    n, ln = p.get("count", 8), p.get("len", 4)
    spin = t*p.get("spin", 0.8)
    col = _tint(_col(p.get("color", "#ffd23f")), tint)
    for k in range(n):
        ang = spin + k*2*math.pi/n
        rl = ln + 0.6*math.sin(t*3+k)
        _set(buf, int(round(cy-math.sin(ang)*rl)), int(round(cx+math.cos(ang)*rl)), col, 0.9)


_FIRE = ["#FFF3C0", "#FFD23F", "#FF7A18", "#E01B1B", "#6B0F0F"]


def _draw_flame(buf, p, t, tint):
    cx = p.get("cx", 4)
    max_h = p.get("height", 12)
    width = p.get("width", 4.6)
    pal = [_tint(_col(c), tint) for c in p.get("palette", _FIRE)]
    for C in range(COLS):
        taper = max(0.0, 1-((C-cx)/width)**2)
        flick = 0.75+0.25*math.sin(t*9+C*1.7)+0.15*_noise(C, int(t*12), 3)
        h = max_h*taper*flick
        for R in range(ROWS):
            fh = ROWS-1-R
            if fh <= h:
                z = fh/max(1.0, h)
                idx = min(len(pal)-2, int(z*(len(pal)-1)))
                fr = z*(len(pal)-1)-idx
                _set(buf, R, C, _lerp3(pal[idx], pal[idx+1], fr))


def _draw_particles(buf, p, t, tint):
    n = p.get("n", 12)
    col = _tint(_col(p.get("color", "#ffffff")), tint)
    motion = p.get("motion", "rise")
    for i in range(n):
        bx = _noise(i, 1)*COLS
        if motion == "rise":
            by = (ROWS - (t*p.get("speed", 4)+i*2)) % ROWS
        elif motion == "fall":
            by = (t*p.get("speed", 4)+i*2) % ROWS
        else:  # swirl
            by = ROWS/2 + math.sin(t*2+i)*4
            bx = COLS/2 + math.cos(t*2+i)*3
        _set(buf, int(by), int(bx), col, 0.7+0.3*_noise(i, int(t*6)))


_PRIMS = {"disc": _draw_disc, "ring": _draw_ring, "crescent": _draw_crescent,
          "line": _draw_line, "tri": _draw_tri, "rect": _draw_rect,
          "rays": _draw_rays, "flame": _draw_flame, "particles": _draw_particles}


def _tint(col, tint):
    """tint = (warmth -0..1 cool..warm, brightness 0..1) or None."""
    if not tint or col is None:
        return col
    warmth, bright = tint
    r, g, b = col
    r = min(1.0, r*(0.85+0.4*warmth))
    b = min(1.0, b*(0.85+0.4*(1-warmth)))
    k = 0.55+0.75*bright
    return (min(1, r*k), min(1, g*k), min(1, b*k))


def mood_tint(state):
    """Map feeling -> (warmth, brightness) applied to every glyph color."""
    warmth = max(0.0, min(1.0, state.valence))
    bright = max(0.15, min(1.0, 0.35 + 0.6*state.arousal + 0.2*(state.valence-0.5)
                           - 0.3*state.saturation))
    return (warmth, bright)


def render_pixels(buf, spec, t):
    """Draw a pixel-art bitmap the AI painted directly: {palette:{char:'#rrggbb'},
    rows:[...]}. '.' / ' ' / '' = off. Centered on the 17x9 body. Lets it draw ANY object."""
    buf[:] = 0.0
    pal = spec.get("palette", {}) or {}
    rows = [r for r in (spec.get("rows") or []) if isinstance(r, str)][:ROWS]
    off_r = max(0, (ROWS - len(rows)) // 2)
    for i, row in enumerate(rows):
        r = off_r + i
        off_c = max(0, (COLS - len(row)) // 2) if len(row) < COLS else 0
        for j, ch in enumerate(row[:COLS]):
            if ch in (" ", ".", "-", "_", ""):
                continue
            hexc = pal.get(ch)
            if not hexc:
                continue
            try:
                _set(buf, r, off_c + j, _col(hexc))
            except Exception:
                continue
    breath = 0.88 + 0.12 * math.sin(t * 1.7)
    try:
        buf *= breath
    except TypeError:
        pass


def render_glyph(buf, glyph, t, tint=None):
    """Draw a glyph dict into buf (float RGB 17x9)."""
    buf[:] = 0.0
    bg = glyph.get("bg")
    if bg:
        base = _tint(_col(bg), tint)
        top = _tint(_col(glyph["bg_top"]), tint) if "bg_top" in glyph else base
        for R in range(ROWS):
            for C in range(COLS):
                _set(buf, R, C, _lerp3(top, base, R/ROWS))
    for layer in glyph.get("layers", []):
        if not isinstance(layer, dict):
            continue
        fn = _PRIMS.get(layer.get("type"))
        if not fn:
            continue
        try:                       # an invented/LLM layer must never crash the body
            fn(buf, layer, t, tint)
        except Exception:
            continue
    # Always-on life: a gentle breathing + slow shimmer so the body is never a still
    # frame — dynamic like a GIF even when the being is holding one feeling.
    breath = 0.86 + 0.14 * math.sin(t * 1.7)
    shimmer = 1.0 + 0.05 * math.sin(t * 5.0)
    try:
        buf *= breath * shimmer
    except TypeError:
        pass
