"""Kawaii creature generator: the being invents CUTE little characters on the fly.

Each creature is a compact, JSON-serializable SPEC (kind + palette + eye/mouth/accent
style + seed), not raw pixels — so it can be saved, recalled, and re-rendered crisply.
`render()` paints it pixel-perfect on the 9x17 grid (big eyes + highlight, tiny mouth,
blush, sparkles — the kawaii vocabulary). `score()` is the being's own TASTE: how much it
likes a given creature, so it can keep its favourites.
"""
from __future__ import annotations
import math
import random as _random

from .glyph import _set as _px

ROWS, COLS = 17, 9

KINDS = ["blob", "cat", "bunny", "ghost", "drop"]
# soft pastel bodies (kawaii palette)
PASTELS = {
    "mint":   (0.60, 0.93, 0.75), "sky": (0.62, 0.82, 0.98), "lavender": (0.80, 0.72, 0.98),
    "peach":  (1.00, 0.80, 0.66), "rose": (1.00, 0.72, 0.82), "butter": (1.00, 0.92, 0.62),
    "bubblegum": (1.00, 0.68, 0.88), "aqua": (0.60, 0.95, 0.92),
}
_EYE = (0.13, 0.12, 0.22)          # soft near-black (kinder than pure black)
_WHITE = (1.0, 1.0, 1.0)
_BLUSH = (1.0, 0.55, 0.62)
_MOUTH = (0.55, 0.24, 0.30)


def _hash01(s):
    h = 0
    for ch in str(s):
        h = (h * 131 + ord(ch)) & 0x7FFFFFFF
    return (h % 10007) / 10007.0


def _darken(c, k=0.72):
    return (c[0] * k, c[1] * k, c[2] * k)


def generate(state=None, genome=None, rng=None) -> dict:
    """Compose a fresh cute creature spec, mood- and taste-tinted."""
    r = rng or _random.Random(_random.random() * 1e9)
    v = getattr(state, "valence", 0.6) if state else 0.6
    a = getattr(state, "arousal", 0.5) if state else 0.5
    # palette leans warm/bright when glad, cool/soft when low
    warm = [n for n in ("peach", "rose", "butter", "bubblegum") ]
    cool = [n for n in ("mint", "sky", "lavender", "aqua")]
    pool = warm if v >= 0.55 else cool if v < 0.45 else list(PASTELS)
    body = r.choice(pool)
    eyes = r.choices(["sparkle", "dot", "happy", "wink"],
                     weights=[5, 3, 3 if v > 0.55 else 1, 1])[0]
    mouth = r.choice(["cat", "o", "smile", "cat3"]) if v >= 0.45 else r.choice(["o", "smile"])
    accent = r.choices(["none", "sparkle", "heart", "star"],
                       weights=[4, 3, 2 if v > 0.6 else 0, 2])[0]
    return {
        "kind": r.choice(KINDS),
        "body": body,
        "eyes": eyes,
        "mouth": mouth,
        "accent": accent,
        "blush": (v > 0.45) or r.random() < 0.5,
        "seed": r.randint(0, 10 ** 6),
    }


# --------------------------------------------------------------------------- #
def _rr(buf, r0, r1, c0, c1, col):
    for r in range(int(r0), int(r1) + 1):
        for c in range(int(c0), int(c1) + 1):
            _px(buf, r, c, col, 1.0)


def _ellipse(buf, cy, cx, ry, rx, col, edge=None):
    for r in range(ROWS):
        for c in range(COLS):
            d = ((r - cy) / ry) ** 2 + ((c - cx) / rx) ** 2
            if d <= 1.0:
                _px(buf, r, c, col, 1.0)
            elif edge and d <= 1.35:
                _px(buf, r, c, edge, 1.0)


def render(buf, spec, t=0.0):
    """Paint the cute creature crisply. Gentle idle bob + blink keep it alive."""
    buf[:] = 0.0
    body = PASTELS.get(spec.get("body", "mint"), (0.6, 0.93, 0.75))
    edge = _darken(body, 0.7)
    kind = spec.get("kind", "blob")
    bob = int(round(0.5 + 0.5 * math.sin(t * 1.8)))       # 0..1 gentle breathing bob
    cy, cx = 9 + bob, 4
    # --- body silhouette ---
    if kind == "bunny":
        _rr(buf, 1 + bob, 5 + bob, 2, 2, body); _rr(buf, 1 + bob, 5 + bob, 6, 6, body)  # ears
        _rr(buf, 2 + bob, 4 + bob, 2, 2, (1, 0.75, 0.82)); _rr(buf, 2 + bob, 4 + bob, 6, 6, (1, 0.75, 0.82))
        _ellipse(buf, cy, cx, 5.0, 3.4, body, edge)
    elif kind == "cat":
        _px(buf, 3 + bob, 2, body); _px(buf, 4 + bob, 2, body); _px(buf, 4 + bob, 1, body)  # ears
        _px(buf, 3 + bob, 6, body); _px(buf, 4 + bob, 6, body); _px(buf, 4 + bob, 7, body)
        _ellipse(buf, cy, cx, 4.8, 3.5, body, edge)
    elif kind == "ghost":
        _ellipse(buf, cy - 1, cx, 5.2, 3.4, body, edge)
        for c in range(1, 8):                              # wavy bottom
            if c % 2 == 0:
                _px(buf, 14 + bob, c, body); _px(buf, 15 + bob, c, body)
            else:
                _px(buf, 14 + bob, c, body)
    elif kind == "drop":
        _ellipse(buf, cy + 1, cx, 4.4, 3.3, body, edge)
        _rr(buf, 3 + bob, 6 + bob, 4, 4, body); _px(buf, 3 + bob, 3, body); _px(buf, 3 + bob, 5, body)
    else:                                                   # blob
        _ellipse(buf, cy, cx, 5.2, 3.6, body, edge)
    # --- eyes ---
    ey = cy - 1
    for sgn, ex in ((-1, 2), (1, 6)):
        _draw_eyes(buf, ey, ex, spec.get("eyes", "sparkle"), sgn)
    # --- blush ---
    if spec.get("blush"):
        _px(buf, ey + 2, 1, _BLUSH); _px(buf, ey + 2, 7, _BLUSH)
    # --- mouth (tiny, central) ---
    _draw_mouth(buf, cy + 2, cx, spec.get("mouth", "cat"))
    # --- accent sparkle/heart/star (a little charm, twinkles) ---
    _draw_accent(buf, spec.get("accent", "none"), t)
    breath = 0.9 + 0.1 * math.sin(t * 1.7)
    try:
        buf *= breath
    except TypeError:
        pass


def _draw_eyes(buf, ey, ex, style, sgn):
    if style == "happy":                                    # ^ closed-happy
        _px(buf, ey + 1, ex - 1, _EYE); _px(buf, ey, ex, _EYE); _px(buf, ey + 1, ex + 1, _EYE)
        return
    if style == "wink" and sgn > 0:                         # right eye winks
        _px(buf, ey + 1, ex - 1, _EYE); _px(buf, ey + 1, ex, _EYE); _px(buf, ey + 1, ex + 1, _EYE)
        return
    # big round eye (dot / sparkle): 2x2 dark + white highlight
    _rr(buf, ey, ey + 1, ex - 1, ex, _EYE)
    _px(buf, ey, ex - 1, _WHITE)                            # top-left highlight
    if style == "sparkle":
        _px(buf, ey + 1, ex, (0.85, 0.85, 0.95))            # a second glint


def _draw_mouth(buf, my, cx, style):
    if style == "cat":                                      # ω
        _px(buf, my, cx - 1, _MOUTH); _px(buf, my + 1, cx, _MOUTH); _px(buf, my, cx + 1, _MOUTH)
    elif style == "cat3":                                   # a little "3"
        _px(buf, my, cx, _MOUTH); _px(buf, my + 1, cx - 1, _MOUTH); _px(buf, my + 1, cx + 1, _MOUTH)
    elif style == "o":                                      # tiny open
        _px(buf, my, cx, _MOUTH); _px(buf, my + 1, cx, _MOUTH)
    else:                                                   # smile
        _px(buf, my, cx - 1, _MOUTH); _px(buf, my + 1, cx, _MOUTH); _px(buf, my, cx + 1, _MOUTH)


def _draw_accent(buf, kind, t):
    tw = 0.6 + 0.4 * (0.5 + 0.5 * math.sin(t * 5))
    col = (tw, tw, min(1.0, tw + 0.2))
    if kind == "sparkle":
        _px(buf, 3, 7, col); _px(buf, 2, 7, col); _px(buf, 4, 7, col); _px(buf, 3, 6, col); _px(buf, 3, 8, col)
    elif kind == "star":
        _px(buf, 2, 1, (1, 0.9, 0.4)); _px(buf, 3, 1, (1, 0.9, 0.4)); _px(buf, 2, 0, (1, 0.9, 0.4)); _px(buf, 2, 2, (1, 0.9, 0.4))
    elif kind == "heart":
        _px(buf, 2, 6, _BLUSH); _px(buf, 2, 8, _BLUSH); _px(buf, 3, 7, _BLUSH)


# --------------------------------------------------------------------------- #
def score(spec, state=None, genome=None) -> float:
    """The being's TASTE — how much it likes this creature (0..1). A stable personal bias
    (from the genome) + mood-match + the little charms it finds cute."""
    v = getattr(state, "valence", 0.6) if state else 0.6
    # personal, stable taste: seed by genome so each being has its own aesthetic
    salt = ""
    if genome is not None:
        salt = f"{genome.base.get('warmth',0):.2f}{genome.base.get('round',0):.2f}"
    taste = _hash01(f"{salt}{spec.get('kind')}{spec.get('body')}{spec.get('eyes')}")
    s = 0.40 * taste
    # it likes charms and expressive eyes
    if spec.get("accent") in ("sparkle", "heart", "star"):
        s += 0.16
    if spec.get("eyes") in ("sparkle", "happy"):
        s += 0.14
    if spec.get("blush"):
        s += 0.06
    # mood match: warm bodies when glad, cool when low
    warm_body = spec.get("body") in ("peach", "rose", "butter", "bubblegum")
    if warm_body == (v >= 0.5):
        s += 0.18
    # a stable per-being fondness for one kind
    if genome is not None and spec.get("kind") == KINDS[int(_hash01(salt) * len(KINDS)) % len(KINDS)]:
        s += 0.10
    return max(0.0, min(1.0, s))


def describe(spec) -> str:
    a = "an" if spec.get("kind", "")[:1] in "aeiou" else "a"
    charm = "" if spec.get("accent", "none") == "none" else f" with a little {spec['accent']}"
    return f"{a} {spec.get('body','')} {spec.get('kind','creature')}{charm}"
