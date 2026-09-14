"""One registry of bold, recognizable, colorful emblems — the being's visual words.

Combines the rich hand-drawn illustrations (fire, heart, wave, sun, moon, eye, boat,
hand) with the DSL-composed ones (star, tree, flower, bird, rain, spiral, key). Each is
exposed as a simple callable render(buf, t) so the transformation engine can morph
between any two. The being (or the AI) picks an emblem by name to express a feeling.
"""
from __future__ import annotations
import numpy as np

from . import emblems as E
from .glyph import render_glyph, ROWS, COLS
from .specs import GLYPHS


def _from_emblem(fn):
    return lambda buf, t: fn(buf, t, 1.0)


def _from_glyph(spec):
    return lambda buf, t: render_glyph(buf, spec, t)


# rich illustrations win for shared names (fire/heart/sun/moon/wave/eye/boat/hand)
REGISTRY = {name: _from_emblem(fn) for name, fn in E.EMBLEMS.items()}
for name, spec in GLYPHS.items():
    REGISTRY.setdefault(name, _from_glyph(spec))

NAMES = sorted(REGISTRY)

# feeling -> the emblem that best expresses it (transformed, never literal)
EMOTION_EMBLEM = {
    "affectionate": "heart", "excited": "fire", "restless": "fire", "alert": "fire",
    "playful": "boat", "serene": "sun", "contemplative": "tree", "curious": "eye",
    "fascinated": "star", "surprised": "star", "melancholic": "moon", "lonely": "moon",
    "overwhelmed": "wave", "suspicious": "eye", "calm": "sun",
}


# several fitting emblems per mood, so the being can re-express the same feeling freshly.
# Kept broad on purpose — waves, boat, hand, bird, key all reachable across moods.
EMOTION_POOL = {
    "serene": ["sun", "flower", "tree", "moon", "hand", "boat"],
    "contemplative": ["tree", "moon", "sun", "hand", "key"],
    "calm": ["sun", "flower", "moon", "hand", "boat"],
    "curious": ["eye", "boat", "key", "star", "hand", "bird"],
    "fascinated": ["star", "eye", "sun", "boat", "key"],
    "affectionate": ["heart", "flower", "sun", "hand", "bird"],
    "playful": ["boat", "star", "bird", "hand", "flower"],
    "excited": ["fire", "star", "bird", "wave", "sun"],
    "restless": ["fire", "wave", "bird", "eye"],
    "alert": ["fire", "eye", "wave"],
    "melancholic": ["moon", "rain", "tree", "wave", "hand"],
    "lonely": ["moon", "rain", "hand", "tree"],
    "overwhelmed": ["wave", "spiral", "rain", "fire"],
    "suspicious": ["eye", "moon", "wave"],
    "surprised": ["star", "eye", "fire", "bird"],
}


def get(name):
    return REGISTRY.get(name)


def variant(state, i: int):
    """A fresh emblem for the current mood — often mood-fitting, sometimes any shape from
    the whole repertoire, so the full variety (waves, boat, hands...) keeps surfacing."""
    import random
    if random.random() < 0.35:                    # wildcard: surprise with any of the 15
        return random.choice(NAMES)
    dom = (state.dominant_emotion or "").lower()
    pool = [n for n in EMOTION_POOL.get(dom, []) if n in REGISTRY] or list(NAMES)
    return pool[i % len(pool)]


def pick(state):
    """Return (name, renderer) for how the being currently feels."""
    dom = (state.dominant_emotion or "curious").lower()
    # a warm, wide-open greeting waves a hand
    if state.social_affinity > 0.7 and state.valence > 0.6 and state.arousal < 0.7:
        name = "hand"
    else:
        name = EMOTION_EMBLEM.get(dom, "sun")
    return name, REGISTRY[name]


def frame_of(name, t=1.5):
    """Render a single still of an emblem (for previews)."""
    buf = np.zeros((ROWS, COLS, 3))
    fn = REGISTRY.get(name)
    if fn:
        fn(buf, t)
    return buf
