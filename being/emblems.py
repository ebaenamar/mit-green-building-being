"""Bold, recognizable emblems — the being's expressive vocabulary.

At 17x9 a detailed scene is illegible; a single strong silhouette is not. Each
emblem is a big centered symbol that stands for an emotion (fire, heart, wave,
sun, moon, eye, boat, hand...), drawn with high contrast and its own motion so
it reads instantly and feels alive.

Every emblem is draw_<name>(buf, t, intensity=1.0), buf = float RGB (17,9,3).
"""
from __future__ import annotations
import math

ROWS, COLS = 17, 9
CX = 4.0


def hx(s):
    s = s.lstrip("#")
    return (int(s[0:2], 16)/255, int(s[2:4], 16)/255, int(s[4:6], 16)/255)


def _set(buf, r, c, col, a=1.0):
    if 0 <= r < ROWS and 0 <= c < COLS and a > 0:
        ia = 1 - a
        buf[r, c, 0] = buf[r, c, 0]*ia + col[0]*a
        buf[r, c, 1] = buf[r, c, 1]*ia + col[1]*a
        buf[r, c, 2] = buf[r, c, 2]*ia + col[2]*a


def _lerp3(a, b, t):
    return (a[0]+(b[0]-a[0])*t, a[1]+(b[1]-a[1])*t, a[2]+(b[2]-a[2])*t)


def _noise(x, y, s=0):
    v = math.sin(x*12.9898 + y*78.233 + s*37.719) * 43758.5453
    return v - math.floor(v)


# --- FIRE — excitement / passion / anger ----------------------------------
_F_WHITE, _F_YEL, _F_ORA, _F_RED, _F_DARK = (
    hx("FFF3C0"), hx("FFD23F"), hx("FF7A18"), hx("E01B1B"), hx("6B0F0F"))


def draw_fire(buf, t, intensity=1.0):
    buf[:] = 0.0
    max_h = 3 + 11 * intensity
    for c in range(COLS):
        taper = max(0.0, 1 - ((c - CX) / 4.6) ** 2)
        flick = 0.75 + 0.25 * math.sin(t * 9 + c * 1.7) + 0.15 * _noise(c, int(t * 12), 3)
        h = max_h * taper * flick
        for r in range(ROWS):
            fh = (ROWS - 1 - r)           # height above the base
            if fh <= h:
                z = fh / max(1.0, h)      # 0 base .. 1 tip
                if z < 0.2:   col = _lerp3(_F_WHITE, _F_YEL, z / 0.2)
                elif z < 0.5: col = _lerp3(_F_YEL, _F_ORA, (z - 0.2) / 0.3)
                elif z < 0.8: col = _lerp3(_F_ORA, _F_RED, (z - 0.5) / 0.3)
                else:         col = _lerp3(_F_RED, _F_DARK, (z - 0.8) / 0.2)
                _set(buf, r, c, col)
    # embers rising
    for i in range(3):
        er = int((ROWS - 1 - (t * 6 + i * 5) % ROWS))
        ec = int(CX + 2.2 * math.sin(t * 3 + i))
        _set(buf, er, ec, _F_YEL, 0.7)


# --- HEART — affection ----------------------------------------------------
_H_RED, _H_HI, _H_DK = hx("FF2D55"), hx("FF8FA8"), hx("8A0B2A")


def draw_heart(buf, t, intensity=1.0):
    buf[:] = 0.0
    beat = 0.9 + 0.12 * (math.sin(t * 4) * 0.5 + 0.5) + 0.06 * (math.sin(t * 8) > 0.6)
    sx, sy = 3.3 * beat, 3.0 * beat
    cy = 7.5
    for r in range(ROWS):
        for c in range(COLS):
            x = (c - CX) / sx
            y = (cy - r) / sy            # y up
            f = (x * x + y * y - 1) ** 3 - x * x * (y ** 3)
            if f <= 0:
                edge = min(1.0, -f * 2.5)
                hi = 1.0 if (x < -0.15 and y > 0.25) else 0.0   # top-left glint
                col = _lerp3(_H_DK, _H_RED, min(1.0, edge + 0.3))
                col = _lerp3(col, _H_HI, 0.6 * hi)
                _set(buf, r, c, col)


# --- WAVE — overwhelmed / flooded / flow ----------------------------------
_W_DEEP, _W_MID, _W_FOAM = hx("0B3D91"), hx("1E7FD8"), hx("DFF6FF")


def draw_wave(buf, t, intensity=1.0):
    buf[:] = 0.0
    amp = 1.5 + 2.5 * intensity
    for c in range(COLS):
        surf = 5 + amp * math.sin(c * 0.9 - t * 3.5) + 1.2 * math.sin(c * 0.4 - t * 1.7)
        for r in range(ROWS):
            if r >= surf:
                depth = (r - surf) / (ROWS - surf + 0.01)
                col = _lerp3(_W_MID, _W_DEEP, depth)
                _set(buf, r, c, col)
            if abs(r - surf) < 0.9:        # foam crest
                _set(buf, r, c, _W_FOAM, 0.9)
    # a curling tip that travels
    tc = int((t * 2.2) % COLS)
    ts = int(5 + amp * math.sin(tc * 0.9 - t * 3.5))
    _set(buf, ts - 1, tc, _W_FOAM)
    _set(buf, ts - 1, min(COLS - 1, tc + 1), _W_FOAM, 0.7)


# --- SUN — joy / serenity / confidence ------------------------------------
_S_CORE, _S_MID, _S_RAY, _S_SKY = hx("FFF6C8"), hx("FFC93C"), hx("FF9A1F"), hx("2A1A4A")


def draw_sun(buf, t, intensity=1.0):
    for r in range(ROWS):                 # dusk sky gradient
        for c in range(COLS):
            _set(buf, r, c, _lerp3(_S_SKY, (0.05, 0.02, 0.12), r / ROWS))
    cy, radius = 8.0, 2.6 + 0.5 * intensity
    for k in range(12):                   # rotating rays
        ang = t * 0.8 + k * math.pi / 6
        rl = radius + 2.2 + 0.6 * math.sin(t * 3 + k)
        rr, rc = cy - math.sin(ang) * rl, CX + math.cos(ang) * rl
        _set(buf, int(round(rr)), int(round(rc)), _S_RAY, 0.9)
    for r in range(ROWS):                 # disc
        for c in range(COLS):
            d = math.hypot(c - CX, r - cy)
            if d <= radius:
                _set(buf, r, c, _lerp3(_S_CORE, _S_MID, d / radius))
            elif d <= radius + 0.7:
                _set(buf, r, c, _S_MID, 0.5)


# --- MOON — melancholy / loneliness ---------------------------------------
_M_PALE, _M_DK, _M_SKY, _M_STAR = hx("EAF0FF"), hx("7C89B8"), hx("0A0E24"), hx("CBD6FF")


def draw_moon(buf, t, intensity=1.0):
    for r in range(ROWS):
        for c in range(COLS):
            _set(buf, r, c, _lerp3(_M_SKY, (0.02, 0.03, 0.08), r / ROWS))
    for i in range(7):                     # twinkling stars
        sr = int(_noise(i, 1) * ROWS)
        sc = int(_noise(i, 2) * COLS)
        tw = 0.4 + 0.6 * (math.sin(t * 3 + i) * 0.5 + 0.5)
        _set(buf, sr, sc, _M_STAR, tw)
    cy, radius = 8.0, 3.6
    for r in range(ROWS):                  # full disc minus an offset disc = crescent
        for c in range(COLS):
            d = math.hypot(c - CX, r - cy)
            d2 = math.hypot(c - (CX + 2.3), r - (cy - 0.6))
            if d <= radius and d2 > radius - 0.2:
                _set(buf, r, c, _lerp3(_M_PALE, _M_DK, d / radius))


# --- EYE — curiosity / watching / suspicion -------------------------------
_E_WHITE, _E_IRIS, _E_IRIS2, _E_PUP, _E_LID = (
    hx("F2F5FF"), hx("29B6D8"), hx("0E6B86"), hx("07121A"), hx("1A2230"))


def draw_eye(buf, t, intensity=1.0):
    buf[:] = 0.0
    cy = 8.5
    blink = (t % 3.6) < 0.16
    gx = 1.3 * math.sin(t * 0.9)           # gaze wanders
    for r in range(ROWS):
        for c in range(COLS):
            x, y = (c - CX) / 4.2, (r - cy) / 2.6      # almond
            if x * x + y * y <= 1.0:
                _set(buf, r, c, _E_WHITE if not blink else _E_LID)
    if not blink:
        ix = CX + gx
        for r in range(ROWS):
            for c in range(COLS):
                d = math.hypot(c - ix, r - cy)
                if d <= 2.0:
                    _set(buf, r, c, _lerp3(_E_IRIS, _E_IRIS2, d / 2.0))
                if d <= 0.95:
                    _set(buf, r, c, _E_PUP)
                if d <= 0.5 and (c - ix) < 0 and (r - cy) < 0:
                    _set(buf, r, c, _E_WHITE, 0.9)      # catch-light
    else:
        for c in range(1, COLS - 1):
            _set(buf, int(cy), c, _E_PUP, 0.7)          # closed lash line


# --- BOAT — journey / curiosity / adventure -------------------------------
_B_HULL, _B_SAIL, _B_SAIL2, _B_MAST, _B_SKY, _B_SEA, _B_FOAM = (
    hx("7A3B12"), hx("F5F0E6"), hx("E4463C"), hx("3A2410"),
    hx("173A6B"), hx("1E6FB0"), hx("Bfe6ff".upper()))


def draw_boat(buf, t, intensity=1.0):
    for r in range(ROWS):                  # sky over sea
        for c in range(COLS):
            _set(buf, r, c, _lerp3(_B_SKY, (0.03, 0.06, 0.14), r / 11))
    rock = 0.9 * math.sin(t * 1.6)         # gentle rocking (columns of the sea)
    sea_top = 12
    for r in range(ROWS):
        for c in range(COLS):
            surf = sea_top + 0.6 * math.sin(c * 1.1 - t * 3)
            if r >= surf:
                _set(buf, r, c, _lerp3(_B_SEA, (0.03, 0.15, 0.3), (r - surf) / 5))
            if abs(r - surf) < 0.6:
                _set(buf, r, c, _B_FOAM, 0.7)
    off = int(round(rock))
    mast_c = 4 + off
    for r in range(3, 12):                  # mast
        _set(buf, r, mast_c, _B_MAST)
    for r in range(3, 11):                  # triangular sail to the right
        w = int((r - 2) * 0.7)
        for c in range(mast_c + 1, min(COLS, mast_c + 1 + w)):
            _set(buf, r, c, _B_SAIL2 if (c == mast_c + w) else _B_SAIL)
    for c in range(mast_c - 2, mast_c + 3):  # hull
        if 0 <= c < COLS:
            _set(buf, 11, c, _B_HULL)
    _set(buf, 12, mast_c, _B_HULL); _set(buf, 12, mast_c - 1, _B_HULL, 0.7)
    _set(buf, 12, mast_c + 1, _B_HULL, 0.7)


# --- HAND — greeting / reaching / connection ------------------------------
_HD_SKIN, _HD_SHAD, _HD_BG = hx("F6B27A"), hx("C97C42"), hx("1a1230".upper())


def draw_hand(buf, t, intensity=1.0):
    for r in range(ROWS):
        for c in range(COLS):
            _set(buf, r, c, _HD_BG)
    tilt = 0.7 * math.sin(t * 3)           # a wave
    palm_top, palm_bot = 9, 15
    for r in range(palm_top, palm_bot):    # palm
        for c in range(2, 7):
            _set(buf, r, c, _HD_SKIN)
    finger_len = [4, 5, 6, 5]              # four fingers
    for i, fl in enumerate(finger_len):
        c = 2 + i + int(round(tilt))
        for r in range(palm_top - fl, palm_top):
            if 0 <= c < COLS and r >= 0:
                _set(buf, r, c, _HD_SKIN)
    tc = 1 + int(round(tilt))              # thumb
    for r in range(palm_top, palm_top + 3):
        if 0 <= tc < COLS:
            _set(buf, r, tc, _HD_SKIN)
    for r in range(palm_top, palm_bot):    # shading on the right edge
        _set(buf, r, 6, _HD_SHAD, 0.5)


EMBLEMS = {"fire": draw_fire, "heart": draw_heart, "wave": draw_wave, "sun": draw_sun,
           "moon": draw_moon, "eye": draw_eye, "boat": draw_boat, "hand": draw_hand}
