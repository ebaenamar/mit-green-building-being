"""PERCEIVE: raw input -> a sensation with inferred properties.

Inputs are not commands. A line of human text arrives as a *sensation* with an
intensity, a tone, a novelty. The mind decides what, if anything, to do with it.
"""
from __future__ import annotations
import re
import time
from dataclasses import dataclass, field

_POS = set(("love like joy happy warm gentle beautiful calm peace kind hello hi friend "
            "wonderful yes please thanks thank soft bright sweet good great amazing "
            "missed glow together close home welcome play playful "
            # español
            "amor amo quiero feliz contento contenta alegre alegria gracias bonito linda "
            "lindo hermoso hermosa genial increible bien bueno buena abrazo cariño hola "
            "encanta guay chulo maravilloso").split())
_NEG = set(("hate angry fear dark cold cruel sad lonely alone pain hurt no stop bad "
            "afraid scared tired sick death die empty lost broken danger chasing chase "
            "threat monster enemy attack help careful "
            # español
            "triste tristeza solo sola miedo dolor mal malo odio llorar lloro muerte "
            "muerto cansado cansada enfermo enferma perdido perdida roto rota adios harto "
            "harta asustado asustada asusta susto preocupado preocupada vacio vacia solo").split())
_HIGH = set(("run fast now loud jump fight chase chasing burn explode wild storm scream "
             "chaos dance quick hurry go energy danger voices shout many attack play "
             # español
             "corre rapido ahora grita fuego fiesta baila energia peligro muchos ataca "
             "susto asusta asustaste vamos salta").split())
_LOW = set(("slow quiet rest sleep still hush whisper calm gentle drift float wait "
            "breathe soft dim cold empty dark alone lonely tired numb faint weak heavy "
            # español
            "lento quieto duerme calma suave frio vacio oscuro cansado triste solo "
            "silencio descansa").split())
# words that pull attention toward the unknown, and words that signal a sensory din
_CURIO = set(("wonder hidden secret mystery what why how explore inside discover unknown "
              "curious question strange").split())
_DIN = set(("loud many voices everyone noise noisy chaos crowd shouting screaming "
            "overwhelm deafening").split())


@dataclass
class Sensation:
    raw: str
    kind: str = "text"
    at: float = field(default_factory=time.time)
    intensity: float = 0.3
    valence_tone: float = 0.5       # 0 unpleasant .. 1 pleasant
    energy_tone: float = 0.5        # 0 calm .. 1 energetic
    novelty: float = 0.5
    curio_tone: float = 0.0        # pull toward the unknown
    din_tone: float = 0.0          # sensory overload / too-many-at-once
    words: tuple = ()

    def describe(self) -> str:
        return (f'sensation<{self.kind}> "{self.raw[:60]}" '
                f'int={self.intensity:.2f} tone={self.valence_tone:.2f} '
                f'energy={self.energy_tone:.2f} novelty={self.novelty:.2f} '
                f'curio={self.curio_tone:.2f} din={self.din_tone:.2f}')


class Perceiver:
    """Keeps a little history so it can judge novelty and persistence."""

    def __init__(self):
        self._recent = []

    def perceive(self, raw: str, kind: str = "text") -> Sensation:
        text = raw.strip()
        words = re.findall(r"[a-zA-Z']+", text.lower())
        wl = len(words)

        exclaim = text.count("!")
        caps = sum(1 for ch in text if ch.isupper())
        cap_ratio = caps / max(1, len(text))
        intensity = min(1.0, 0.2 + 0.05 * wl + 0.15 * exclaim + 0.6 * cap_ratio)

        pos = sum(w in _POS for w in words)
        neg = sum(w in _NEG for w in words)
        valence_tone = 0.5 + 0.12 * (pos - neg)
        valence_tone = max(0.0, min(1.0, valence_tone))

        hi = sum(w in _HIGH for w in words)
        lo = sum(w in _LOW for w in words)
        energy_tone = 0.5 + 0.12 * (hi - lo) + 0.1 * exclaim + 0.3 * cap_ratio
        energy_tone = max(0.0, min(1.0, energy_tone))

        seen = sum(1 for r in self._recent if r == text.lower())
        novelty = max(0.05, 1.0 - 0.4 * seen)

        curio_tone = min(1.0, 0.45 * sum(w in _CURIO for w in words) + (0.25 if "?" in text else 0.0))
        din_tone = min(1.0, 0.4 * sum(w in _DIN for w in words))

        self._recent.append(text.lower())
        self._recent = self._recent[-12:]
        return Sensation(raw=text, kind=kind, intensity=intensity,
                         valence_tone=valence_tone, energy_tone=energy_tone,
                         novelty=novelty, curio_tone=curio_tone, din_tone=din_tone,
                         words=tuple(words))
