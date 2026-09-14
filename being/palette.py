"""Color helpers. The being's skin colors are derived from how it feels, not from
what a human 'asked for'. Emotional state in -> a small palette of RGB floats out.
"""
from __future__ import annotations
import colorsys
from dataclasses import dataclass


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if x < lo else hi if x > hi else x


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * clamp(t)


def hsv(h: float, s: float, v: float):
    """HSV (all 0..1, hue wraps) -> (r, g, b) floats in 0..1."""
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, clamp(s), clamp(v))
    return (r, g, b)


@dataclass
class Palette:
    """A handful of colors the current mood paints with (all RGB floats 0..1)."""
    ground: tuple      # dim ambient tint filling the dark
    form: tuple        # the main body of the archetype
    accent: tuple      # highlights, sparks, iris, petal tips
    spark: tuple       # the 'I noticed you' flash color


def mood_palette(s) -> Palette:
    """Translate an EmotionalState into color.

    valence  -> hue (cool/blue when low, warm/gold when high)
    curiosity-> pulls the accent toward a contrasting, 'unresolved' hue
    arousal  -> vividness and brightness
    saturation (overload) -> washes color out toward grey/fragmentation
    coherence-> how close accent sits to form (harmony vs tension)
    """
    # Base hue: 0.60 (blue) at valence 0 -> 0.09 (warm amber) at valence 1.
    hue = lerp(0.60, 0.09, s.valence)
    # Loneliness / low social affinity cools things slightly toward indigo.
    hue = clamp(hue + (0.05 * (1.0 - s.social_affinity)))

    overload = s.saturation
    sat = clamp(0.30 + 0.65 * s.arousal - 0.45 * overload)
    val = clamp(0.20 + 0.75 * (0.4 + 0.6 * s.arousal) - 0.15 * overload)

    form = hsv(hue, sat, val)
    ground = hsv(hue, clamp(sat * 0.7), clamp(0.06 + 0.10 * s.valence))

    # Accent hue drifts away from the form hue; curiosity widens the gap,
    # low coherence makes it clash (near-complementary), high coherence keeps it close.
    gap = lerp(0.03, 0.5, clamp(0.5 * s.curiosity + 0.5 * (1.0 - s.coherence)))
    accent = hsv(hue + gap, clamp(sat + 0.2), clamp(val + 0.2))

    # Spark is a bright, slightly warm attention flash tuned by valence.
    spark = hsv(lerp(0.14, 0.02, s.valence), 0.85, 1.0)
    return Palette(ground=ground, form=form, accent=accent, spark=spark)
