"""The screen is the being's body. When someone asks to see a part of it or a gesture —
"show me your face / your nose / your hand", "wave", "walk", "smile", "look" — it shows it
RIGHT NOW, animated, without waiting on the language model. Deterministic and instant.
"""
from __future__ import annotations
import math

from .glyph import _set, ROWS, COLS
from .render import draw_face
from . import emblems as E

SCAL = ("valence", "arousal", "curiosity", "openness", "confidence",
        "saturation", "social_affinity", "coherence")

SKIN, SKIN_DK = (0.96, 0.63, 0.27), (0.75, 0.45, 0.16)
GREEN, GREEN_DK = (0.0, 0.78, 0.0), (0.0, 0.47, 0.0)
DARK = (0.14, 0.09, 0.06)
MOUTH = (0.6, 0.06, 0.08)


def draw_nose(buf, t):
    buf[:] = 0.0
    bob = int(round(0.6 * math.sin(t * 4)))          # gentle sniff
    for r in range(3, 13):
        w = (r - 2) // 2
        for c in range(4 - w, 4 + w + 1):
            _set(buf, r + bob, c, SKIN if c != 4 else SKIN_DK)
    _set(buf, 12 + bob, 3, DARK); _set(buf, 12 + bob, 5, DARK)   # nostrils


def draw_walk(buf, t):
    buf[:] = 0.0
    phase = int((t * 4) % 2)                          # two-step cycle
    bob = int(round(0.5 * math.sin(t * 8)))
    cx = 4
    _set(buf, 4 + bob, cx, SKIN)                      # head
    for r in range(5, 9):                             # body
        _set(buf, r + bob, cx, GREEN)
        _set(buf, r + bob, cx - 1, GREEN_DK)
        _set(buf, r + bob, cx + 1, GREEN_DK)
    # arms swing opposite to legs
    _set(buf, 6 + bob, cx - 2, SKIN if phase == 0 else DARK)
    _set(buf, 6 + bob, cx + 2, SKIN if phase == 1 else DARK)
    # legs alternate
    if phase == 0:
        _set(buf, 9 + bob, cx - 1, GREEN); _set(buf, 10 + bob, cx - 2, GREEN_DK)
        _set(buf, 9 + bob, cx + 1, GREEN); _set(buf, 10 + bob, cx + 1, GREEN_DK)
    else:
        _set(buf, 9 + bob, cx - 1, GREEN); _set(buf, 10 + bob, cx - 1, GREEN_DK)
        _set(buf, 9 + bob, cx + 1, GREEN); _set(buf, 10 + bob, cx + 2, GREEN_DK)


def draw_mouth(buf, t, emo):
    buf[:] = 0.0
    val = emo.get("valence", 0.6)
    open_amt = 0.5 + 0.5 * math.sin(t * 6)           # talking
    for c in range(2, 7):                             # lips
        _set(buf, 9, c, MOUTH)
    h = int(round(1 + open_amt * 2))
    for dr in range(1, h):
        for c in range(3, 6):
            _set(buf, 9 + dr, c, MOUTH)
    if val > 0.6:                                     # smile corners up
        _set(buf, 8, 2, MOUTH); _set(buf, 8, 6, MOUTH)


def make_gesture(name, state):
    emo = {k: getattr(state, k) for k in SCAL}
    if name == "face":
        return lambda buf, t: draw_face(buf, emo, t)
    if name == "wave":
        return lambda buf, t: E.draw_hand(buf, t, 1.0)
    if name == "eye":
        return lambda buf, t: E.draw_eye(buf, t, 1.0)
    if name == "nose":
        return draw_nose
    if name == "walk":
        return draw_walk
    if name == "mouth":
        return lambda buf, t: draw_mouth(buf, t, emo)
    return None


# keyword -> gesture (English + Spanish); first hit wins
_KW = [
    ("walk", ("walk", "anda", "andar", "camina", "caminar", "muévete", "muevete", "move")),
    ("wave", ("wave", "saluda", "saludar", "saludo", "hand", "mano")),
    ("nose", ("nose", "nariz", "smell", "oler", "huele", "sniff")),
    ("mouth", ("mouth", "boca", "talk to me", "habla")),
    ("eye", ("eye", "ojo", "ojos", "blink", "parpad")),
    ("face", ("face", "rostro", "cara", "smile", "sonr", "yourself", "your body",
              "tu cuerpo", "cómo eres", "como eres", "qué eres", "que eres")),
]
# a request to SHOW, or a direct action verb — otherwise we don't fire on a passing mention
_SHOW = ("show", "see ", "muestra", "muéstra", "muestrame", "muéstrame", "ensen", "enseñ",
         "let me see", "puedo ver", "quiero ver", "give me", "hazme", "haz una", "haz un")
_ACTION = ("wave", "saluda", "saludo", "walk", "camina", "anda ", "andar", "muévete", "muevete",
           "smile", "sonr", "blink", "parpad")


def detect(text: str):
    """Return a gesture name if the message asks to see a body part / do a gesture."""
    s = (text or "").lower()
    if not (any(w in s for w in _SHOW) or any(a in s for a in _ACTION)):
        return None
    for name, kws in _KW:
        if any(k in s for k in kws):
            return name
    return None
