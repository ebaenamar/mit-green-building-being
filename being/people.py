"""The people it knows. Being remembered is one of the strongest signs that something is alive:
the building recognises someone who comes back, remembers what they told it, and thinks about
them when it's alone ("did Ana pass her exam?").

Separate from the fading trace memory — these relationships persist (to disk) across restarts.
"""
from __future__ import annotations
import json
import random
import time

from .jsonio import atomic_write

_GENERIC = {"someone", "anon", "anonymous", "guest", "user", "solo", ""}


def _ago(secs: float) -> str:
    if secs < 90:
        return "just now"
    if secs < 3600:
        return f"{int(secs // 60)} min ago"
    if secs < 86400:
        return f"{int(secs // 3600)} h ago"
    d = int(secs // 86400)
    return "yesterday" if d == 1 else f"{d} days ago"


class People:
    def __init__(self, path: str = "", cap: int = 400):
        self.path = path
        self.cap = cap
        self.people = {}          # key(lower name) -> record
        try:
            with open(path) as fh:
                self.people = json.load(fh) or {}
        except (OSError, ValueError):
            self.people = {}

    @staticmethod
    def _key(name):
        k = (name or "").strip().lower()
        return "" if k in _GENERIC else k

    def brief(self, name: str) -> str:
        """What the being knows about this person, BEFORE this message (for the mind)."""
        k = self._key(name)
        if not k:
            return ""
        p = self.people.get(k)
        if not p:
            return (f"You've never met {name} before — this is the first time they talk to you. "
                    f"Notice them; you'll remember them.")
        said = "; ".join(f"'{s}'" for s in p.get("said", [])[-3:])
        line = (f"You KNOW {p['name']}: this is visit #{p.get('visits', 1) + 1}, last here "
                f"{_ago(time.time() - p.get('last', time.time()))}.")
        if said:
            line += f" Things they told you before: {said}."
        if p.get("felt"):
            line += f" Last time they seemed {p['felt']}."
        line += (" Greet them like someone you know — reference what they told you when it fits "
                 "(ask how it went), don't recite it.")
        return line

    def seen(self, name: str, text: str, felt: str = ""):
        k = self._key(name)
        if not k:
            return
        now = time.time()
        p = self.people.get(k) or {"name": name.strip()[:24], "first": now, "last": 0.0,
                                   "visits": 0, "said": []}
        if now - p.get("last", 0.0) > 1800:            # a new visit after 30 min apart
            p["visits"] = p.get("visits", 0) + 1
        p["last"] = now
        t = (text or "").strip()
        if len(t) >= 6:                                 # keep the substantive things they say
            p["said"] = (p.get("said", []) + [t[:90]])[-5:]
        if felt:
            p["felt"] = felt
        self.people[k] = p
        if len(self.people) > self.cap:                 # forget the longest-absent first
            for kk in sorted(self.people, key=lambda x: self.people[x].get("last", 0))[:len(self.people) - self.cap]:
                self.people.pop(kk, None)

    def someone_to_think_about(self):
        """A person it might wonder about when alone (recent + substantive), or None."""
        now = time.time()
        cands = [p for p in self.people.values()
                 if p.get("said") and now - p.get("last", 0) > 600 and now - p.get("last", 0) < 7 * 86400]
        if not cands:
            return None
        p = random.choice(sorted(cands, key=lambda x: -x.get("last", 0))[:8])
        return (f"you're thinking about {p['name']} (last talked {_ago(now - p['last'])}); they "
                f"told you: '{p['said'][-1]}'. Wonder about them, or about how that went.")

    def known_names(self, n: int = 5):
        ps = sorted(self.people.values(), key=lambda x: -x.get("last", 0))
        return [p["name"] for p in ps[:n]]

    def __len__(self):
        return len(self.people)

    def save(self):
        atomic_write(self.path, self.people)
