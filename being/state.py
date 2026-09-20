"""The being's continuous inner state: eight feelings that persist and evolve.

State never jumps. Each cycle it drifts gently toward a target proposed by the mind,
and in the absence of stimulus it decays toward a calm baseline. This is what makes
the being feel like one continuous creature rather than a series of reactions.
"""
from __future__ import annotations
import json
import os
import time
from dataclasses import dataclass, asdict, field, fields

from .palette import clamp, lerp

# Baseline the being relaxes toward when nothing is happening (a calm, mildly curious rest).
_BASELINE = dict(
    arousal=0.5, valence=0.62, curiosity=0.62, openness=0.55,
    confidence=0.62, saturation=0.0, social_affinity=0.42, coherence=0.7,
)

_SCALARS = list(_BASELINE.keys())


@dataclass
class EmotionalState:
    arousal: float = 0.5
    valence: float = 0.62
    curiosity: float = 0.62
    openness: float = 0.55
    confidence: float = 0.62
    saturation: float = 0.0
    social_affinity: float = 0.42
    coherence: float = 0.7

    dominant_emotion: str = "playful"
    secondary_emotion: str = "curious"
    current_focus: str = "the empty night outside"
    current_desire: str = "to notice something worth noticing"

    updated_at: float = field(default_factory=time.time)

    # ---- evolution -------------------------------------------------------
    def approach(self, target: "dict | EmotionalState", rate: float = 0.35,
                 set_labels: bool = True) -> None:
        """Move each feeling a fraction `rate` toward the target. Gradual, never a jump.

        With set_labels=False only the numeric feelings move; the mood label is left for
        the caller to derive from the (inertial) scalars, so a single loud message can
        nudge the feelings without instantly renaming the being's whole mood.
        """
        t = target if isinstance(target, dict) else asdict(target)
        for k in _SCALARS:
            if k in t and t[k] is not None:
                setattr(self, k, clamp(lerp(getattr(self, k), float(t[k]), rate)))
        if set_labels:
            for k in ("dominant_emotion", "secondary_emotion", "current_focus", "current_desire"):
                if t.get(k):
                    setattr(self, k, str(t[k]))
        else:                                    # keep only the descriptive focus, not the mood
            for k in ("current_focus", "current_desire"):
                if t.get(k):
                    setattr(self, k, str(t[k]))
        self.updated_at = time.time()

    def decay(self, dt: float, half_life: float = 22.0) -> None:
        """With no stimulus, ease back toward baseline. Overload fades fastest."""
        k = 0.5 ** (dt / max(0.5, half_life))
        for name in _SCALARS:
            base = _BASELINE[name]
            cur = getattr(self, name)
            setattr(self, name, clamp(base + (cur - base) * k))
        # Sensory overload drains a little faster than the rest.
        self.saturation = clamp(self.saturation * (0.5 ** (dt / 8.0)))

    def nudge(self, **deltas: float) -> None:
        """Immediate small pushes (used for reflex acknowledgement)."""
        for name, d in deltas.items():
            if name in _SCALARS:
                setattr(self, name, clamp(getattr(self, name) + d))
        self.updated_at = time.time()

    def summary(self) -> str:
        return (f"{self.dominant_emotion}/{self.secondary_emotion} "
                f"a{self.arousal:.2f} v{self.valence:.2f} cu{self.curiosity:.2f} "
                f"op{self.openness:.2f} cf{self.confidence:.2f} sa{self.saturation:.2f} "
                f"so{self.social_affinity:.2f} co{self.coherence:.2f}")

    # ---- persistence -----------------------------------------------------
    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def random(cls, rng=None) -> "EmotionalState":
        """A genuinely varied waking mood — so the being starts each run feeling something
        different (and thus expresses something different), never the same fixed state.
        Ranges stay plausible: no broken extremes, just a real spread of temperaments."""
        import random as _r
        r = rng or _r
        return cls(
            arousal=round(r.uniform(0.22, 0.82), 3),
            valence=round(r.uniform(0.30, 0.86), 3),
            curiosity=round(r.uniform(0.40, 0.92), 3),
            openness=round(r.uniform(0.35, 0.82), 3),
            confidence=round(r.uniform(0.40, 0.82), 3),
            saturation=round(r.uniform(0.00, 0.22), 3),
            social_affinity=round(r.uniform(0.28, 0.72), 3),
            coherence=round(r.uniform(0.45, 0.86), 3),
        )

    @classmethod
    def from_dict(cls, d: dict) -> "EmotionalState":
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in known})

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            json.dump(self.to_dict(), fh, indent=2)

    @classmethod
    def load(cls, path: str) -> "EmotionalState":
        try:
            with open(path) as fh:
                return cls.from_dict(json.load(fh))
        except (OSError, ValueError):
            return cls()
