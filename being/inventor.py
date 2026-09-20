"""Invent new emblems from an interaction, instead of only picking from a fixed set.

The being reaches for a seed symbol its feeling suggests, then *transforms* it:
recolours it by mood, jitters and scales its parts, and — when it feels mixed things —
fuses two seeds into a genuinely new symbol. What a human says can bias which seeds it
reaches for (never copied literally: a mention of the sea may surface a wave or a moon).
Invented glyphs are named and remembered, so the repertoire grows with the relationship.

When OpenAI credits exist, mind.py asks the model to compose the glyph in this same DSL;
this procedural inventor is the always-available stand-in and the few-shot seed source.
"""
from __future__ import annotations
import copy
import hashlib
import json
import os

from .specs import GLYPHS, EMOTION_GLYPH
from .glyph import _col

# words humans might say -> a seed the feeling can *reach for* (transformed, not mirrored)
NOUN_BIAS = {
    "sea": "wave", "ocean": "wave", "water": "wave", "wave": "wave", "rain": "rain",
    "fire": "fire", "burn": "fire", "sun": "sun", "light": "sun", "warm": "sun",
    "moon": "moon", "night": "moon", "star": "star", "sky": "star",
    "love": "heart", "heart": "heart", "tree": "tree", "forest": "tree",
    "flower": "flower", "bird": "bird", "fly": "bird", "key": "key", "door": "key",
}

_WARM = ("#ff2d55", "#ff7a18", "#ffd23f", "#ff9a1f", "#ff4d8d")
_COOL = ("#29b6d8", "#4846ff", "#8a5cff", "#68a8ff", "#c9a7ff")


def _rng(seed):
    h = int(hashlib.md5(str(seed).encode()).hexdigest(), 16)
    while True:
        h = (h * 1103515245 + 12345) & 0x7FFFFFFF
        yield (h % 1000) / 1000.0


def _shift_color(hexc, warmth):
    r, g, b = _col(hexc)
    r = min(1.0, r * (0.8 + 0.5 * warmth))
    b = min(1.0, b * (0.8 + 0.5 * (1 - warmth)))
    return "#%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255))


def _mutate(glyph, state, gen):
    g = copy.deepcopy(glyph)
    warm = state.valence
    for layer in g.get("layers", []):
        if "cx" in layer:
            layer["cx"] = max(0.5, min(8.5, layer["cx"] + (next(gen) - 0.5) * 1.2))
        if "cy" in layer:
            layer["cy"] = max(1.0, min(15.0, layer["cy"] + (next(gen) - 0.5) * 1.2))
        if "r" in layer:
            layer["r"] = max(0.6, layer["r"] * (0.85 + 0.4 * state.arousal))
        for key in ("color", "edge"):
            if key in layer and next(gen) < 0.6:
                layer[key] = _shift_color(layer[key], warm)
        if next(gen) < 0.35 * state.arousal:
            layer["anim"] = layer.get("anim", "pulse")
    # high arousal adds motion; overload adds a swirl of particles
    if state.arousal > 0.6:
        g.setdefault("layers", []).append(
            {"type": "particles", "n": int(4 + 10 * state.arousal),
             "color": _WARM[int(next(gen) * len(_WARM))] if warm > 0.5 else _COOL[int(next(gen) * len(_COOL))],
             "motion": "swirl" if state.saturation > 0.5 else "rise", "anim": "twinkle"})
    return g


def _fuse(a, b, gen):
    """Fuse two seeds: all of A, plus A's signature layer shrunk and offset from B."""
    g = copy.deepcopy(a)
    donor = [l for l in b.get("layers", []) if l.get("type") in
             ("disc", "crescent", "ring", "tri", "flame", "rays")]
    if donor:
        sig = copy.deepcopy(donor[int(next(gen) * len(donor))])
        if "r" in sig:
            sig["r"] = max(0.7, sig["r"] * 0.55)
        if "cx" in sig:
            sig["cx"] = 4 + (next(gen) - 0.5) * 3
        if "cy" in sig:
            sig["cy"] = 4 + next(gen) * 2
        sig["anim"] = "pulse"
        g.setdefault("layers", []).append(sig)
    return g


def invent(state, words=(), memory_words=()):
    """Return (name, glyph) transformed from the being's feeling and the interaction."""
    dom = state.dominant_emotion or "curious"
    sec = state.secondary_emotion or ""
    seed_a = EMOTION_GLYPH.get(dom, "star")
    # a human's noun can bias the *secondary* reach (not the dominant feeling)
    bias = None
    for w in list(words) + list(memory_words):
        if w in NOUN_BIAS:
            bias = NOUN_BIAS[w]
            break
    seed_b = bias or EMOTION_GLYPH.get(sec, seed_a)

    tag = hashlib.md5(f"{dom}{sec}{bias}{state.summary()}".encode()).hexdigest()[:3]
    gen = _rng(tag)
    base = _mutate(GLYPHS.get(seed_a, GLYPHS["star"]), state, gen)
    if seed_b != seed_a and (0.35 < state.valence < 0.75 or state.curiosity > 0.55):
        base = _fuse(base, GLYPHS.get(seed_b, GLYPHS["star"]), gen)
        name = f"{dom}-{seed_a}x{seed_b}-{tag}"
    else:
        name = f"{dom}-{seed_a}-{tag}"
    return name, base


class Library:
    """The being's growing repertoire. Two tiers:
      * glyphs  — every symbol it has ever composed (a big loose bag).
      * forms   — symbols it HELD long enough to truly learn, each tagged with the mood it
                  was in. These it can deliberately RETURN to when it feels that way again,
                  the way a person falls back into a familiar expression.
    """

    def __init__(self, path):
        self.path = path
        self.glyphs = {}
        self.forms = []          # [{name, spec, mood:{dominant,valence,arousal,curiosity}}]
        try:
            with open(path) as fh:
                data = json.load(fh)
            if isinstance(data, dict) and ("glyphs" in data or "forms" in data):
                self.glyphs = data.get("glyphs", {}) or {}
                self.forms = data.get("forms", []) or []
            elif isinstance(data, dict):
                self.glyphs = data           # legacy: a plain dict of name -> glyph
        except (OSError, ValueError):
            pass

    def remember(self, name, glyph):
        if name not in self.glyphs:
            self.glyphs[name] = glyph

    def learn(self, name, spec, state):
        """Consolidate a form the being held long enough, tagged with the current mood, so
        it can be recalled later. Idempotent by name; keeps the most recent ~60."""
        if any(f.get("name") == name for f in self.forms):
            return False
        self.forms.append({"name": name, "spec": spec, "mood": {
            "dominant": getattr(state, "dominant_emotion", ""),
            "valence": round(getattr(state, "valence", 0.5), 3),
            "arousal": round(getattr(state, "arousal", 0.5), 3),
            "curiosity": round(getattr(state, "curiosity", 0.5), 3)}})
        self.forms = self.forms[-60:]
        return True

    def recall(self, state, jitter=0.12):
        """Return (name, spec) of a learned form whose mood is closest to how it feels now
        (a little randomized, so it doesn't always snap to the same one). None if empty."""
        import random
        if not self.forms:
            return None
        def dist(f):
            m = f.get("mood", {})
            d = (abs(m.get("valence", 0.5) - state.valence)
                 + abs(m.get("arousal", 0.5) - state.arousal)
                 + 0.5 * abs(m.get("curiosity", 0.5) - getattr(state, "curiosity", 0.5)))
            if m.get("dominant") and m["dominant"] == state.dominant_emotion:
                d -= 0.4                                   # same named mood pulls strongly
            return d + random.uniform(0, jitter)
        f = min(self.forms, key=dist)
        return f["name"], f["spec"]

    def save(self):
        if not self.path:
            return
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w") as fh:
            json.dump({"glyphs": self.glyphs, "forms": self.forms}, fh)

    def __len__(self):
        return len(self.glyphs)
