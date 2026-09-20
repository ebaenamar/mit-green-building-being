"""An evolving morphology: the being's body isn't a fixed recipe, it has a GENOME that
mutates slowly and is shaped by what it lives through — so its face, its eye, its hand
keep changing over the relationship, yet always stay recognizably its own.

Two layers, like a real body:
  * base — the slowly EVOLVING self. Interactions and input `imprint` tiny, lasting nudges
    (warm talk rounds and opens it; tension sharpens it; novelty widens its eyes; being
    seen opens it up). It persists across runs, so the body genuinely develops.
  * cur  — the LIVING form. Each tick it drifts (mutates) around base, so nothing is ever
    frozen; but it always returns toward base, so identity holds. This is why the being's
    eye today looks like a mutation of its eye yesterday, not a brand-new random eye.

`express(part, state)` blends the genome (who it has become) with the current mood (how it
feels right now) into geometry the anatomy composer draws. Genes are clamped to ranges that
keep an eye an eye — it evolves, but stays representative.
"""
from __future__ import annotations
import json
import os
import random
import time

# gene -> (low, high, init). Kept semantic and bounded so forms stay recognizable.
GENES = {
    "size":          (0.85, 1.15, 1.00),   # overall scale
    "warmth":        (0.20, 0.90, 0.55),   # palette warm(1)/cool(0) bias
    "asym":          (0.00, 0.28, 0.06),   # left/right character
    "eye_open":      (0.55, 1.00, 0.85),   # lid rest / aspect
    "iris":          (0.40, 0.72, 0.55),   # iris size (fraction of eye)
    "pupil":         (0.30, 0.60, 0.42),   # pupil dilation (fraction of iris)
    "slant":         (-0.8, 0.8, 0.05),    # eye/brow slant (character)
    "spacing":       (0.82, 1.22, 1.00),   # eye spacing in the face
    "blink":         (0.55, 1.30, 0.90),   # blink rate
    "round":         (0.35, 0.85, 0.60),   # head/palm roundness
    "finger_len":    (0.35, 0.85, 0.60),   # finger length
    "finger_spread": (0.30, 0.90, 0.55),   # finger spread
    "mouth_w":       (0.40, 0.85, 0.60),   # mouth width
    "brow":          (0.20, 0.85, 0.50),   # brow prominence
}


def _clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


class Genome:
    def __init__(self, path: str = ""):
        self.path = path
        self.base = {k: init for k, (_, _, init) in GENES.items()}
        self.cur = dict(self.base)
        self.age = 0.0            # seconds of lived time (a soft measure of how developed)
        self.imprints = 0        # how many interactions have shaped it
        self._last = time.time()
        self._load()

    # -- evolution (lasting) ----------------------------------------------
    def imprint(self, state=None, sensation=None, impact=None, weight=1.0):
        """A lived moment leaves a tiny, LASTING mark on the base genome. Many such marks,
        over many interactions, are what make the body slowly become its own."""
        s = 0.022 * weight        # per-interaction step is deliberately small
        val = getattr(state, "valence", 0.5) if state else 0.5
        aro = getattr(state, "arousal", 0.5) if state else 0.5
        cur = getattr(state, "curiosity", 0.5) if state else 0.5
        soc = getattr(state, "social_affinity", 0.5) if state else 0.5
        # tone of the specific thing that just arrived (if any)
        vt = getattr(sensation, "valence_tone", val) if sensation else val
        nov = getattr(sensation, "novelty", cur) if sensation else cur

        def push(gene, amt):
            lo, hi, _ = GENES[gene]
            self.base[gene] = _clamp(self.base[gene] + amt, lo, hi)

        # warm, pleasant contact -> rounder, more open, warmer, wider-mouthed
        push("warmth", s * (vt - 0.5) * 2)
        push("round", s * (vt - 0.5) * 1.4)
        push("eye_open", s * (vt - 0.5) * 1.2)
        push("mouth_w", s * (vt - 0.5) * 1.0)
        # tension / unpleasantness -> sharper slant, narrower eyes
        push("slant", s * (0.5 - vt) * 1.6)
        push("brow", s * (aro - 0.5) * 1.4)
        # novelty & curiosity -> wider eyes (bigger iris & pupil)
        push("iris", s * (nov - 0.5) * 1.4 + s * (cur - 0.5))
        push("pupil", s * (aro - 0.5) * 1.2 + s * (nov - 0.5))
        # being attended to -> opens up, eyes settle a touch closer (engaged)
        push("spacing", -s * (soc - 0.5) * 0.8)
        push("eye_open", s * (soc - 0.5) * 0.8)
        # hands echo energy: livelier -> longer, more spread fingers
        push("finger_len", s * (aro - 0.5) * 1.0)
        push("finger_spread", s * (aro - 0.5) * 1.0)
        # if its expressions land poorly, it grows a little more asymmetric/searching
        if impact is not None:
            push("asym", s * (0.5 - impact) * 0.8)
        self.imprints += 1

    # -- mutation (living jitter around base) -----------------------------
    def tick(self, dt: float, energy: float = 0.5):
        """Drift the living form around the base each moment: never frozen, always returns
        toward the evolving base so identity persists. `energy` (arousal) widens the wander."""
        self.age += dt
        wander = 0.06 * (0.4 + energy)
        pull = min(1.0, dt * 0.5)                  # return toward base
        for k, (lo, hi, _) in GENES.items():
            span = hi - lo
            target = self.base[k] + random.uniform(-1, 1) * wander * span
            self.cur[k] = _clamp(self.cur[k] + (target - self.cur[k]) * pull, lo, hi)

    # -- read the form ----------------------------------------------------
    def express(self, part: str, state=None) -> dict:
        """Blend the genome (who it is) with the mood (how it feels now) into geometry the
        anatomy composer draws. Mood modulates on top of the slowly-evolving body."""
        g = dict(self.cur)
        val = getattr(state, "valence", 0.5) if state else 0.5
        aro = getattr(state, "arousal", 0.5) if state else 0.5
        cur = getattr(state, "curiosity", 0.5) if state else 0.5
        # live mood shifts (transient, not stored): feeling changes the reading of the body
        p = {
            "size": g["size"] * (0.96 + 0.08 * aro),
            "warmth": _clamp(0.6 * g["warmth"] + 0.4 * val, 0, 1),
            "asym": g["asym"],
            "eye_open": _clamp(g["eye_open"] * (0.9 + 0.2 * (0.5 + 0.5 * (aro - 0.3))), 0.45, 1.05),
            "iris": _clamp(g["iris"] + 0.10 * (cur - 0.5), 0.35, 0.78),
            "pupil": _clamp(g["pupil"] + 0.18 * (aro - 0.5), 0.25, 0.66),   # dilates when roused
            "slant": g["slant"] + 0.4 * (aro - 0.5) - 0.3 * (val - 0.5),
            "spacing": g["spacing"],
            "blink": g["blink"] * (0.8 + 0.6 * aro),
            "round": g["round"],
            "finger_len": g["finger_len"],
            "finger_spread": _clamp(g["finger_spread"] + 0.15 * (aro - 0.5), 0.2, 0.95),
            "mouth_w": g["mouth_w"],
            "mouth_curve": (val - 0.5) * 2,     # smile/frown is mostly live feeling
            "brow": g["brow"],
        }
        return p

    def summary(self) -> str:
        devel = "newborn" if self.imprints < 15 else "forming" if self.imprints < 80 else "developed"
        return (f"morphology[{devel}] imprints={self.imprints} "
                f"warmth={self.cur['warmth']:.2f} eye_open={self.cur['eye_open']:.2f} "
                f"iris={self.cur['iris']:.2f} slant={self.cur['slant']:+.2f} round={self.cur['round']:.2f}")

    # -- persistence ------------------------------------------------------
    def _load(self):
        if not self.path:
            return
        try:
            with open(self.path) as fh:
                d = json.load(fh)
            for k in GENES:
                if k in d.get("base", {}):
                    lo, hi, _ = GENES[k]
                    self.base[k] = _clamp(float(d["base"][k]), lo, hi)
            self.cur = dict(self.base)
            self.age = float(d.get("age", 0.0))
            self.imprints = int(d.get("imprints", 0))
        except (OSError, ValueError):
            pass

    def save(self):
        if not self.path:
            return
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w") as fh:
                json.dump({"base": self.base, "age": round(self.age, 1),
                           "imprints": self.imprints}, fh, indent=2)
        except OSError:
            pass


def default_params(part: str = "") -> dict:
    """Neutral geometry for previews/tests when there's no genome or mood."""
    return Genome().express(part)
