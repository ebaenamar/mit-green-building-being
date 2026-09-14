"""MEMORY: keep meaningful traces, not everything. Memory slowly shapes personality.

Each trace has an importance; recall favours the important and the recent, and
importance decays so old, unreinforced traces fade. Traces persist to disk so the
being wakes up as the same creature it fell asleep as.
"""
from __future__ import annotations
import json
import os
import time


class Memory:
    def __init__(self, path: str, capacity: int = 120):
        self.path = path
        self.capacity = capacity
        self.traces = []
        self._load()

    def _load(self):
        try:
            with open(self.path) as fh:
                self.traces = json.load(fh)
        except (OSError, ValueError):
            self.traces = []

    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w") as fh:
            json.dump(self.traces[-self.capacity:], fh, indent=2)

    def remember(self, text: str, importance: float = 0.5, mood: str = "",
                 influence: bool = True):
        text = (text or "").strip()
        if not text:
            return
        for tr in self.traces:                       # reinforce a repeat
            if tr["text"].lower() == text.lower():
                tr["importance"] = min(1.0, tr["importance"] + 0.15)
                tr["count"] = tr.get("count", 1) + 1
                tr["at"] = time.time()
                return
        self.traces.append({"text": text, "importance": float(importance),
                            "mood": mood, "influence": bool(influence),
                            "at": time.time(), "count": 1})
        self.traces = self.traces[-self.capacity:]

    def decay(self, dt: float, half_life: float = 900.0):
        k = 0.5 ** (dt / half_life)
        for tr in self.traces:
            tr["importance"] *= k
        self.traces = [tr for tr in self.traces if tr["importance"] > 0.05]

    def recall(self, n: int = 5):
        now = time.time()
        ranked = sorted(
            self.traces,
            key=lambda tr: tr["importance"] + 0.3 / (1 + (now - tr["at"]) / 60.0),
            reverse=True,
        )
        return ranked[:n]

    def recall_text(self, n: int = 5) -> str:
        return "; ".join(f'{tr["text"]} (imp {tr["importance"]:.2f})'
                         for tr in self.recall(n)) or "nothing yet"
