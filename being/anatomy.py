"""A self-aware body composer: the being BUILDS a recognizable form from named parts,
in the moment, knowing what the form is made of and what it needs to make it.

Unlike the fixed gestures in gestures.py (a single pre-drawn hand/eye played back), each
builder here ASSEMBLES the part from primitives on the 9x17 body, parametrically — a
different pose/size/spread every time, but always big and recognizable. Crucially each
builder returns a MANIFEST: the parts it used and a plain-language "what it needs" line,
so the being can say "an eye needs a white, an iris, a pupil, a lid to blink, and a
glint — watch me make one." Forms are plain DSL dicts (see glyph.py), so a form held
long enough can be LEARNED (persisted) and returned to later (see inventor.Library).

Builders: eye (blinks, looks around), hand (palm + five fingers, waves), face, mouth
(smiles/talks), nose. Anything abstract (a feeling, not a body part) is left to the
procedural inventor.
"""
from __future__ import annotations
import math
import random as _random

from .glyph import _set as _px

ROWS, COLS = 17, 9

# body palette
_SKIN = "#f6b27a"
_SKIN_DK = "#c98650"
_NAIL = "#ffe0c2"
_DARK = "#241812"
_WHITE = "#fbfbff"
_GREY = "#c7cede"
_LIP = "#d64a5a"
_LIP_DK = "#a83442"


def _hex(r, g, b):
    return "#%02x%02x%02x" % (max(0, min(255, int(r))), max(0, min(255, int(g))),
                              max(0, min(255, int(b))))


def _P(params):
    """Params from the genome, or neutral defaults if none supplied (previews/tests)."""
    if params:
        return params
    from .morphogen import default_params
    return default_params()


def _skin(p):
    """Skin tone shifted by the warmth gene (cool sand -> warm tan)."""
    w = p.get("warmth", 0.55)
    return _hex(210 + 40 * w, 150 + 30 * (0.5 - abs(w - 0.5)), 90 + 60 * (1 - w))


def _iris_color(p):
    """Iris color from the warmth gene (which itself blends the being's mood + genome):
    warm ambers when warm, cool teals/blues when cool."""
    w = p.get("warmth", 0.55)
    if w >= 0.5:
        return _hex(120 + 150 * (w - 0.5) * 2, 90 + 60 * w, 30)          # amber/hazel
    return _hex(40, 110 + 80 * (0.5 - w) * 2, 150 + 100 * (0.5 - w) * 2)  # teal/blue


def _rng(state, salt=0):
    # a small living jitter on top of the genome (kept tiny; the genome carries identity)
    return _random.Random(_random.random() * 1e9 + salt)


# --------------------------------------------------------------------------- #
def eye(state, params=None, r=None):
    """A big eye grown from the genome: white, iris (size/colour from genes+mood) that looks
    around, pupil (dilates with arousal), lids that narrow with eye_open, a blink and a glint.
    Its exact shape is this being's own, and drifts as the genome evolves."""
    p = _P(params)
    r = r or _rng(state, 1)
    sz = p["size"]
    cx = 4
    cy = 8 + r.uniform(-0.3, 0.3)
    look = p["slant"] * 1.6 + r.uniform(-0.4, 0.4)      # gaze from slant gene
    ewhite = 4.2 * sz
    iris_r = p["iris"] * ewhite
    skin = _skin(p)
    layers = [
        {"type": "disc", "cx": cx, "cy": cy, "r": ewhite, "color": _WHITE, "edge": _GREY},
        {"type": "disc", "cx": cx, "cy": cy, "r": ewhite - 0.8, "color": _WHITE},
        {"type": "disc", "cx": cx + look, "cy": cy, "r": iris_r, "color": _iris_color(p),
         "edge": _DARK, "anim": "sway", "anim_amt": 1.0, "anim_speed": 0.6},
        {"type": "disc", "cx": cx + look, "cy": cy, "r": p["pupil"] * iris_r, "color": "#0a0a0a",
         "anim": "sway", "anim_amt": 1.0, "anim_speed": 0.6},
        {"type": "disc", "cx": cx + look - 0.7, "cy": cy - 0.9, "r": 0.5 * sz, "color": _WHITE,
         "anim": "sway", "anim_amt": 1.0, "anim_speed": 0.6},
    ]
    # narrower eye_open -> skin lids intrude from top and bottom (a squint / a wide stare)
    cover = (1.0 - p["eye_open"]) * 3.2
    if cover > 0.3:
        layers.append({"type": "rect", "x": 0, "y": cy - ewhite, "w": COLS, "h": cover + 0.5,
                       "color": skin, "anim": "sway", "anim_amt": p["slant"] * 0.6})
        layers.append({"type": "rect", "x": 0, "y": cy + ewhite - cover, "w": COLS,
                       "h": cover + 0.5, "color": skin})
    # the blinking lid, rate from the blink gene
    layers.append({"type": "rect", "x": 0, "y": cy - 5, "w": COLS, "h": 10, "color": skin,
                   "anim": "blink", "anim_speed": p["blink"]})
    spec = {"bg": "#0a0a12", "layers": layers}
    manifest = {
        "name": "eye",
        "parts": ["the white", "an iris", "a pupil", "a glint", "an eyelid that blinks"],
        "needs": "a white, an iris the color of my mood, a pupil, one spark of light, "
                 "and a lid to blink with",
    }
    return spec, manifest


def hand(state, params=None, r=None):
    """An open hand grown from the genome: palm + four fingers + thumb, where finger length
    and spread come from genes (livelier moods reach longer/wider). Waves (sways)."""
    p = _P(params)
    r = r or _rng(state, 2)
    sway = {"anim": "sway", "anim_amt": 0.9 + 0.8 * p["finger_spread"], "anim_speed": r.uniform(0.8, 1.2)}
    skin = _skin(p)
    palm_top = 10.0
    layers = [{"type": "rect", "x": 1.0, "y": palm_top, "w": 6.6, "h": 4.3,
               "color": skin, "edge": _SKIN_DK, **sway}]
    # four fingers as crisp 1px LINES; spread gene sets column spacing (gaps must stay), length
    # gene sets how far they reach up. Outer fingers a touch shorter.
    gap = 1.55 + 0.5 * p["finger_spread"]                  # ~1.55..2.05
    reach = 2.5 + 5.0 * p["finger_len"]                    # rows above the palm
    for i in range(4):
        fc = 4 + (i - 1.5) * gap
        fc = max(0.6, min(8.4, fc))
        short = 1.4 if i == 0 else 0.7 if i == 3 else 0.0
        top = palm_top - reach + short + r.uniform(-0.3, 0.3)
        layers.append({"type": "line", "x1": fc, "y1": top, "x2": fc, "y2": palm_top + 0.5,
                       "color": skin, **sway})
        layers.append({"type": "disc", "cx": fc, "cy": top, "r": 0.45, "color": _NAIL, **sway})
    # thumb sticking out from the right side of the palm
    layers.append({"type": "line", "x1": 7.4, "y1": palm_top + 1.0, "x2": 8.4, "y2": palm_top + 2.2,
                   "color": skin, **sway})
    layers.append({"type": "disc", "cx": 8.2, "cy": palm_top + 2.2, "r": 0.7, "color": skin, **sway})
    spec = {"bg": "#0a0e18", "layers": layers}
    manifest = {
        "name": "hand",
        "parts": ["a palm", "four fingers", "a thumb", "fingernails"],
        "needs": "a palm and five fingers — four across the top, a thumb off the side",
    }
    return spec, manifest


def mouth(state, params=None, r=None):
    """Lips that curve with feeling (smile/flat/downturn) and widen with the mouth_w gene;
    they part a little (pulse) as if speaking."""
    p = _P(params)
    cy = 9
    curve = p["mouth_curve"] * 3.0             # up when glad, down when low
    w = 2.1 + 1.4 * p["mouth_w"]
    corner = w * 0.62
    layers = [
        {"type": "disc", "cx": 4, "cy": cy, "r": w, "color": _LIP, "edge": _LIP_DK,
         "anim": "pulse", "anim_amt": 0.8},
        {"type": "disc", "cx": 4, "cy": cy + 0.4, "r": w * 0.55, "color": _DARK,
         "anim": "pulse", "anim_amt": 1.2},          # the opening, "talking"
        {"type": "disc", "cx": 4 - corner, "cy": cy - curve * 0.4, "r": 0.8, "color": _LIP},
        {"type": "disc", "cx": 4 + corner, "cy": cy - curve * 0.4, "r": 0.8, "color": _LIP},
    ]
    spec = {"bg": "#0a0508", "layers": layers}
    kind = "a smile" if curve > 0.4 else "a flat line" if curve > -0.4 else "a downturn"
    manifest = {"name": "mouth", "parts": ["upper lip", "lower lip", "the opening", "two corners"],
                "needs": f"two lips, an opening to speak with, and corners — {kind} for how I feel"}
    return spec, manifest


def nose(state, params=None, r=None):
    """A nose: a bridge down the center and two nostrils, width from genes, sniffing gently."""
    p = _P(params)
    skin = _skin(p)
    spread = 1.1 + 1.4 * p["finger_spread"]        # reuse spread gene for nostril width
    sw = {"anim": "sway", "anim_amt": 0.4, "anim_speed": 1.6}
    layers = [
        {"type": "tri", "pts": [[4, 3.5], [4 - spread, 12], [4 + spread, 12]], "color": skin, **sw},
        {"type": "rect", "x": 3.6, "y": 4, "w": 0.9, "h": 8, "color": _SKIN_DK, **sw},
        {"type": "disc", "cx": 4 - spread * 0.7, "cy": 12, "r": 0.8, "color": _DARK, **sw},
        {"type": "disc", "cx": 4 + spread * 0.7, "cy": 12, "r": 0.8, "color": _DARK, **sw},
    ]
    spec = {"bg": "#0a0a12", "layers": layers}
    manifest = {"name": "nose", "parts": ["the bridge", "two nostrils"],
                "needs": "a bridge down the middle and two nostrils to sniff with"}
    return spec, manifest


def face(state, params=None, r=None):
    """A whole face grown from the genome: a head, two eyes that blink (spacing, iris, pupil,
    slant all from genes+mood), brows, a nose, and a mouth that curves with feeling. A slight
    asymmetry gene gives it character. This is the being's OWN face — it drifts as it evolves."""
    p = _P(params)
    r = r or _rng(state, 5)
    skin = _skin(p)
    iris = _iris_color(p)
    curve = p["mouth_curve"] * 3.0
    ex = 1.35 + 0.7 * (p["spacing"] - 0.82) / 0.4        # eye spread from spacing gene
    ey = 6.5
    slant = p["slant"]
    asym = p["asym"]
    head_r = 4.2 + 0.7 * p["round"]
    layers = [{"type": "disc", "cx": 4, "cy": 8.5, "r": head_r, "color": skin, "edge": _SKIN_DK}]
    for k, sgn in enumerate((-1, 1)):
        cx = 4 + sgn * ex
        eyr = (1.05 + 0.35 * p["iris"]) * (1 + (asym if sgn > 0 else -asym) * 0.6)
        layers += [
            {"type": "disc", "cx": cx, "cy": ey + sgn * slant * 0.6, "r": eyr, "color": _WHITE},
            {"type": "disc", "cx": cx, "cy": ey + sgn * slant * 0.6, "r": 0.6 * p["iris"] / 0.55, "color": iris},
            {"type": "disc", "cx": cx, "cy": ey + sgn * slant * 0.6, "r": 0.32 * (1 + p["pupil"]), "color": "#0a0a0a"},
            {"type": "rect", "x": cx - 1.4, "y": ey - 1.6, "w": 2.8, "h": 3.2, "color": skin,
             "anim": "blink", "anim_speed": p["blink"] * (1.05 if k else 0.95)},
        ]
    # brows: prominence from brow gene, tilt from slant
    bt = slant * 1.2
    bw = 0.7 + 0.5 * p["brow"]
    layers += [
        {"type": "line", "x1": 4 - ex - bw, "y1": ey - 2 + bt, "x2": 4 - ex + bw,
         "y2": ey - 2 - bt * 0.3, "color": _DARK},
        {"type": "line", "x1": 4 + ex - bw, "y1": ey - 2 - bt * 0.3, "x2": 4 + ex + bw,
         "y2": ey - 2 + bt, "color": _DARK},
        {"type": "line", "x1": 4, "y1": 8, "x2": 4, "y2": 10, "color": _SKIN_DK},
        {"type": "disc", "cx": 4, "cy": 11.5, "r": 1.1 + 0.7 * p["mouth_w"], "color": _LIP,
         "anim": "pulse", "anim_amt": 0.6},
        {"type": "disc", "cx": 4 - (1.2 + p["mouth_w"]), "cy": 11.5 - curve * 0.4, "r": 0.6, "color": _LIP},
        {"type": "disc", "cx": 4 + (1.2 + p["mouth_w"]), "cy": 11.5 - curve * 0.4, "r": 0.6, "color": _LIP},
    ]
    spec = {"bg": "#0a0a14", "layers": layers}
    manifest = {"name": "face", "parts": ["a head", "two eyes that blink", "brows", "a nose", "a mouth"],
                "needs": "a head, two eyes with lids to blink, brows, a nose, and a mouth"}
    return spec, manifest


# --------------------------------------------------------------------------- #
# A crisp, EXPRESSIVE creature face (pixel-art idiom, not blurry discs). The being is the
# Green Building, so it wears a green kawaii/emoji-style face whose EYES, BROWS and MOUTH
# change shape with emotion — the way readable pixel faces are actually built.
def _S(buf, r, c, rgb):
    _px(buf, int(round(r)), int(round(c)), rgb, 1.0)


def _face_palette(p, v):
    w = p.get("warmth", 0.55)
    # green creature skin: teal when cool, yellow-green when warm
    face = (0.16 + 0.42 * w, 0.60 + 0.20 * w, 0.55 - 0.27 * w)
    out = (face[0] * 0.32, face[1] * 0.32, face[2] * 0.32)
    return {"face": face, "out": out, "white": (0.97, 0.98, 1.0),
            "pupil": (0.05, 0.06, 0.09), "mouth": (0.42, 0.06, 0.10),
            "teeth": (1.0, 0.98, 0.98), "blush": (1.0, 0.52, 0.58)}


def _mode(state):
    v = getattr(state, "valence", 0.6)
    a = getattr(state, "arousal", 0.5)
    if a > 0.74:
        return "surprised"
    if v > 0.66:
        return "happy"
    if v < 0.38 and a > 0.5:
        return "angry"
    if v < 0.42:
        return "sad"
    if a < 0.32:
        return "sleepy"
    return "neutral"


def _draw_eye(buf, er, cols, mode, look, blink, pal):
    """cols = the two columns of this eye (e.g. (2,3))."""
    cL, cR = cols
    if blink or mode == "sleepy":
        _S(buf, er + 1, cL, pal["out"]); _S(buf, er + 1, cR, pal["out"])
        return
    tall = mode == "surprised"
    rows = (er - 1, er, er + 1) if tall else (er, er + 1)
    for r in rows:                                   # the white
        _S(buf, r, cL, pal["white"]); _S(buf, r, cR, pal["white"])
    # pupil: inner column by default, shifted by gaze; lower row when sad
    pr = (er + 1) if mode in ("sad",) else (er if not tall else er)
    pc = cL if look < 0 else cR if look > 0 else (cL if (cL + cR) % 2 == 0 else cR)
    _S(buf, pr, pc, pal["pupil"])
    if tall:                                         # big startled pupil + glint
        _S(buf, pr + 1, pc, pal["pupil"])
    else:
        _S(buf, er, cL if pc == cR else cR, pal["white"])  # glint on the other side
    if mode == "angry":                              # heavy upper lid narrows the eye
        _S(buf, er, cL, pal["out"]); _S(buf, er, cR, pal["out"])


def _draw_brow(buf, br, cols, mode, pal):
    cL, cR = cols
    o = pal["out"]
    if mode == "angry":                              # inner ends DOWN  (\  on left)
        if cL < 4:
            _S(buf, br, cL, o); _S(buf, br + 1, cR, o)
        else:
            _S(buf, br + 1, cL, o); _S(buf, br, cR, o)
    elif mode == "sad":                              # inner ends UP  (/  on left)
        if cL < 4:
            _S(buf, br + 1, cL, o); _S(buf, br, cR, o)
        else:
            _S(buf, br, cL, o); _S(buf, br + 1, cR, o)
    elif mode == "surprised":                        # raised, high & flat
        _S(buf, br - 1, cL, o); _S(buf, br - 1, cR, o)
    elif mode in ("neutral", "happy"):
        _S(buf, br, cL, o); _S(buf, br, cR, o)


def _draw_mouth(buf, mr, mode, pal):
    m, tth = pal["mouth"], pal["teeth"]
    if mode == "happy":                              # open grin with a tooth line
        for c in (2, 3, 4, 5, 6):
            _S(buf, mr, c, m)
        _S(buf, mr - 1, 2, m); _S(buf, mr - 1, 6, m)     # corners up
        for c in (3, 4, 5):
            _S(buf, mr + 1, c, m)
        _S(buf, mr, 3, tth); _S(buf, mr, 5, tth)
    elif mode == "surprised":                        # small open 'o'
        _S(buf, mr, 4, m); _S(buf, mr + 1, 4, m)
        _S(buf, mr, 3, m); _S(buf, mr, 5, m)
    elif mode in ("sad", "angry"):                   # frown (concave down)
        for c in (3, 4, 5):
            _S(buf, mr, c, m)
        _S(buf, mr + 1, 2, m); _S(buf, mr + 1, 6, m)     # corners down
    else:                                            # neutral: gentle small smile
        for c in (3, 4, 5):
            _S(buf, mr, c, m)
        _S(buf, mr - 1, 2, m); _S(buf, mr - 1, 6, m)


def face_render(state, params=None, mode_override=None):
    """Return (render_fn, manifest): a crisp, expressive green creature face painted pixel by
    pixel, whose eyes/brows/mouth reshape with feeling. `mode_override` forces a specific
    emotion (so the face can REACT to a message), else it reads the mood."""
    p = _P(params)
    man = {"name": "face",
           "parts": ["a head", "two eyes", "brows", "a mouth", "blush"],
           "needs": "a rounded head, two big eyes, a pair of brows, and a mouth — their "
                    "shapes are how I show what I feel"}

    def fn(buf, t):
        buf[:] = 0.0
        pal = _face_palette(p, getattr(state, "valence", 0.6))
        mode = mode_override or _mode(state)
        cx, cy = 4.0, 8.7
        rx = 3.1 + 0.5 * p.get("round", 0.6)
        ry = 5.9
        # inside/outline of a rounded head
        inside = [[((c - cx) / rx) ** 2 + ((r - cy) / ry) ** 2 <= 1.0
                   for c in range(COLS)] for r in range(ROWS)]
        for r in range(ROWS):
            for c in range(COLS):
                if inside[r][c]:
                    edge = (r == 0 or c == 0 or r == ROWS - 1 or c == COLS - 1
                            or not inside[r - 1][c] or not inside[r + 1][c]
                            or not inside[r][c - 1] or not inside[r][c + 1])
                    _S(buf, r, c, pal["out"] if edge else pal["face"])
        # gaze + blink from time / genes
        look = 0
        s = math.sin(t * 0.7)
        if s > 0.5:
            look = 1
        elif s < -0.5:
            look = -1
        look += (1 if p.get("slant", 0) > 0.4 else -1 if p.get("slant", 0) < -0.4 else 0)
        look = max(-1, min(1, look))
        blink = ((t * 0.5 * p.get("blink", 0.9)) % 1.0) < 0.06
        er = 6
        _draw_eye(buf, er, (2, 3), mode, look, blink, pal)
        _draw_eye(buf, er, (5, 6), mode, look, blink, pal)
        _draw_brow(buf, er - 2, (2, 3), mode, pal)
        _draw_brow(buf, er - 2, (5, 6), mode, pal)
        _draw_mouth(buf, 11, mode, pal)
        if getattr(state, "valence", 0.6) > 0.62:        # blush when warm/glad
            _S(buf, 9, 1, pal["blush"]); _S(buf, 9, 7, pal["blush"])
        breath = 0.9 + 0.1 * math.sin(t * 1.7)
        try:
            buf *= breath
        except TypeError:
            pass

    return fn, man


BUILDERS = {"eye": eye, "hand": hand, "mouth": mouth, "nose": nose, "face": face}


def render_for(name, state, params=None):
    """Unified dispatch: return (render_fn, manifest, dsl_spec_or_None) for a body part.
    Faces use the crisp expressive painter (no serializable spec); other parts return a DSL
    spec too, so they can still be learned/recalled."""
    if name == "face":
        fn, man = face_render(state, params)
        return fn, man, None
    spec, man = build(name, state, params)
    if not spec:
        return None, None, None
    from .glyph import render_glyph
    return (lambda buf, t, g=spec: render_glyph(buf, g, t)), man, spec

# a request to SHOW/DO, plus the body-part keywords (English + Spanish)
_SHOW = ("show", "see ", "look at", "muestra", "muéstra", "muestrame", "muéstrame",
         "ensen", "enseñ", "let me see", "puedo ver", "quiero ver", "give me", "hazme",
         "haz una", "haz un", "make me", "become")
_PARTS = [
    ("hand", ("hand", "mano", "wave", "saluda", "saludo", "palm", "palma", "fingers", "dedos")),
    ("nose", ("nose", "nariz", "smell", "oler", "huele", "sniff")),
    ("mouth", ("mouth", "boca", "lips", "labios", "talk to me", "habla", "smile", "sonr")),
    ("eye", ("eye", "ojo", "ojos", "blink", "parpad", "look at me", "mírame", "mirame")),
    ("face", ("face", "rostro", "cara", "yourself", "your body", "tu cuerpo",
              "cómo eres", "como eres", "qué eres", "que eres")),
]


def _fold(s):
    """lowercase + strip accents, so 'enséñame' matches 'ensen' etc."""
    import unicodedata
    s = (s or "").lower()
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def detect(text):
    """If the message asks the being to SHOW/make a body part, return its name; else None."""
    s = _fold(text)
    action = ("wave", "saluda", "blink", "parpad", "smile", "sonr", "sniff", "huele")
    if not any(_fold(w) in s for w in _SHOW) and not any(a in s for a in action):
        return None
    for name, kws in _PARTS:
        if any(_fold(k) in s for k in kws):
            return name
    return None


def build(name, state, params=None):
    """Return (spec, manifest) for a named body part built fresh from the current feeling and
    the being's evolving morphology (params from a Genome; neutral defaults if None)."""
    fn = BUILDERS.get(name)
    if not fn:
        return None, None
    return fn(state, params)


def construction_line(manifest):
    """A plain-language line the being can say about what it's making and what it needs —
    so it clearly KNOWS the form it is building (used verbatim by the reflex mind, and as
    grounding context for the language model)."""
    if not manifest:
        return ""
    art = "an" if manifest["name"][:1] in "aeiou" else "a"
    return f"{art} {manifest['name']}? that's {manifest['needs']}. watch — i'll build it."
