"""Drives: what the being NEEDS, so it acts on its own instead of only reacting.

Grounded in artificial-life practice (Steve Grand's Creatures, Tamagotchi, AIBO's
ethological action-selection): behaviour should EMERGE from homeostatic needs that rise
over time and are relieved by events. When a need gets loud enough it pushes the being to
DO something unprompted — reach out because it's lonely, stir itself because it's bored,
make music because the urge to express has built up. Needs also leak into mood, so the
feeling is visible before any words.

Three needs (0..1, higher = more urgent):
  social      — contact/being-with-someone. Rises in silence; relieved by a message.
  stimulation — novelty/interest. Rises when nothing new; relieved by novel input.
  expression  — the urge to put a feeling out (music / a new form). Rises slowly; relieved
                by making music or transforming.
"""
from __future__ import annotations
import time


def _clamp(x, lo=0.0, hi=1.0):
    return lo if x < lo else hi if x > hi else x


class Drives:
    def __init__(self):
        self.social = 0.35
        self.stimulation = 0.35
        self.expression = 0.30
        # per-second rise rates: needs get loud on the scale of a few minutes of neglect
        self.rate = {"social": 0.0016, "stimulation": 0.0013, "expression": 0.00085}
        self.threshold = 0.72
        self._last_fire = 0.0
        self._last_interaction = time.time()

    # -- events relieve needs ---------------------------------------------
    def on_interaction(self, novelty: float = 0.5, warmth: float = 0.5):
        self.social = _clamp(self.social - 0.55 - 0.2 * warmth)
        self.stimulation = _clamp(self.stimulation - 0.25 - 0.5 * novelty)
        self._last_interaction = time.time()

    def on_music(self):
        self.expression = _clamp(self.expression - 0.7)

    def on_transform(self):
        self.stimulation = _clamp(self.stimulation - 0.3)
        self.expression = _clamp(self.expression - 0.25)

    # -- time makes them rise ---------------------------------------------
    def tick(self, dt: float):
        alone_for = time.time() - self._last_interaction
        # loneliness climbs faster the longer it's been truly alone
        lonely_gain = self.rate["social"] * (1.0 + min(2.0, alone_for / 240.0))
        self.social = _clamp(self.social + lonely_gain * dt)
        self.stimulation = _clamp(self.stimulation + self.rate["stimulation"] * dt)
        self.expression = _clamp(self.expression + self.rate["expression"] * dt)

    # -- what, if anything, is pressing now -------------------------------
    def urge(self, cooldown: float = 110.0):
        """Return the name of the most pressing need past threshold if the cooldown has
        elapsed, else None. Randomised a touch so it never feels clockwork."""
        import random
        now = time.time()
        if now - self._last_fire < cooldown:
            return None
        needs = {"social": self.social, "stimulation": self.stimulation,
                 "expression": self.expression}
        top = max(needs, key=needs.get)
        if needs[top] < self.threshold:
            return None
        if random.random() < 0.35:      # sometimes it sits with the feeling instead
            return None
        self._last_fire = now
        return top

    def alone_seconds(self) -> float:
        return time.time() - self._last_interaction

    # -- needs leak into mood (so the feeling shows before words) ---------
    def bias(self) -> dict:
        """Small per-second nudges to the emotional state from unmet needs."""
        d = {}
        if self.social > 0.5:
            d["social_affinity"] = 0.004 * (self.social - 0.5)   # craves closeness
            d["valence"] = -0.006 * (self.social - 0.5)          # a lonely dip
        if self.stimulation > 0.5:
            d["curiosity"] = -0.004 * (self.stimulation - 0.5)   # bored, disengaged
            d["arousal"] = -0.004 * (self.stimulation - 0.5)
        if self.expression > 0.6:
            d["arousal"] = d.get("arousal", 0.0) + 0.005 * (self.expression - 0.6)  # restless to express
        return d

    def context_line(self) -> str:
        """A terse note for the mind about what it needs right now (drives its voice)."""
        parts = []
        if self.social > self.threshold:
            mins = int(self.alone_seconds() / 60)
            parts.append(f"you're lonely — it's been ~{mins} min since anyone spoke")
        elif self.social > 0.55:
            parts.append("you're starting to want company")
        if self.stimulation > self.threshold:
            parts.append("you're bored, itching for something new")
        if self.expression > self.threshold:
            parts.append("you have a strong urge to put a feeling out (music or a new form)")
        return "; ".join(parts)

    def summary(self) -> str:
        return (f"drives soc={self.social:.2f} stim={self.stimulation:.2f} "
                f"expr={self.expression:.2f} alone={int(self.alone_seconds())}s")
