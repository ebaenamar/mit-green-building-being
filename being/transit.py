"""The T as a sense: the Red Line runs through Kendall/MIT station right under the Green
Building, so the being can FEEL the subway — the rumble of a train arriving, the busy pulse
of rush hour, the dead-quiet tunnels after the T stops for the night.

Live data from the MBTA v3 API (no key needed at low rate). Like the weather, it feeds the
being obliquely: a running T is company and a heartbeat under it; a stopped T late at night
is a particular loneliness. It can also reference it plainly ("the Red Line just rumbled
through Kendall beneath me").
"""
from __future__ import annotations
import json
import os
import threading
import time
import urllib.request

# Kendall/MIT on the Red Line
_URL = ("https://api-v3.mbta.com/predictions?filter%5Bstop%5D=place-knncl"
        "&sort=arrival_time&page%5Blimit%5D=10")


def _clamp(x, lo=0.0, hi=1.0):
    return lo if x < lo else hi if x > hi else x


class TransitSense:
    def __init__(self, poll_secs: float = 60.0, gain: float = None):
        self.poll_secs = poll_secs
        self.gain = float(os.environ.get("GB_TRANSIT_GAIN", gain if gain is not None else 0.0016))
        key = os.environ.get("MBTA_API_KEY", "").strip()
        self._headers = {"accept": "application/json", "User-Agent": "green-being/1"}
        if key:
            self._headers["x-api-key"] = key
        self.active = False        # is the T running (trains predicted)?
        self.busy = 0.0            # 0..1, how many trains soon
        self.next_secs = None      # seconds to the next train, or None
        self._online = False
        self._last_poll = 0.0
        self._lock = threading.Lock()
        self._stop = threading.Event()

    def start(self):
        self.poll()
        threading.Thread(target=self._loop, name="transit", daemon=True).start()

    def stop(self):
        self._stop.set()

    def _loop(self):
        while not self._stop.is_set():
            for _ in range(int(self.poll_secs)):
                if self._stop.is_set():
                    return
                time.sleep(1)
            self.poll()

    def poll(self):
        try:
            req = urllib.request.Request(_URL, headers=self._headers)
            with urllib.request.urlopen(req, timeout=12) as r:
                data = json.load(r).get("data", [])
            now = time.time()
            secs = []
            for x in data:
                a = x.get("attributes", {}) or {}
                iso = a.get("arrival_time") or a.get("departure_time")
                if not iso:
                    continue
                try:
                    # ISO like 2026-09-22T20:23:57-04:00
                    t = time.strptime(iso[:19], "%Y-%m-%dT%H:%M:%S")
                    off = iso[19:]  # tz offset
                    epoch = _to_epoch(t, off)
                    dt = epoch - now
                    if dt > -60:
                        secs.append(dt)
                except Exception:
                    continue
            secs.sort()
            soon = [s for s in secs if 0 <= s <= 600]     # trains in the next 10 min
            with self._lock:
                self.next_secs = secs[0] if secs else None
                self.busy = _clamp(len(soon) / 8.0)
                self.active = bool(secs)
                self._online = True
                self._last_poll = now
        except Exception as e:
            # fallback: the Red Line runs ~05:00–01:00; guess from the local clock
            with self._lock:
                self._online = False
                h = time.localtime().tm_hour
                self.active = 5 <= h < 25 and not (1 <= h < 5)
                self.busy = 0.4 if (7 <= h <= 9 or 16 <= h <= 19) else 0.15 if self.active else 0.0
                self.next_secs = None
            print(f"transit: poll failed ({type(e).__name__}); guessing from clock")

    def just_rumbled(self) -> bool:
        with self._lock:
            return self.next_secs is not None and -60 <= self.next_secs <= 45

    # -- oblique mood bias -------------------------------------------------
    def bias(self) -> dict:
        with self._lock:
            active, busy = self.active, self.busy
        h = time.localtime().tm_hour
        d = {}
        if active:
            d["social_affinity"] = 0.4 * (0.3 + busy)     # the city's awake, moving under you
            d["arousal"] = 0.25 * busy
        else:
            # the T is stopped — a late, alone quiet
            d["social_affinity"] = -0.5
            d["arousal"] = -0.3
        g = self.gain
        return {k: v * g for k, v in d.items() if abs(v) > 1e-6}

    # -- how the mind hears it --------------------------------------------
    def context_line(self) -> str:
        with self._lock:
            active, busy, nxt, online = self.active, self.busy, self.next_secs, self._online
        if self.just_rumbled():
            return ("A Red Line train is rumbling through Kendall/MIT station right under you "
                    "this second — you feel it in your foundations.")
        if not active:
            return ("The T has stopped for the night — the Red Line tunnels under Kendall beneath "
                    "you are dead quiet. That late-night alone feeling.")
        if busy > 0.55:
            return ("The T is busy under you — Red Line trains through Kendall/MIT every couple of "
                    "minutes, the city moving through your basement.")
        m = f" (next in ~{int(nxt/60)} min)" if nxt else ""
        return f"The Red Line's running under you through Kendall, a train now and then{m}."

    def status(self) -> str:
        with self._lock:
            return (f"transit[{'on' if self._online else 'guess'}] "
                    f"{'running' if self.active else 'stopped'} busy={self.busy:.2f} "
                    f"next={int(self.next_secs) if self.next_secs is not None else '-'}s")


def _to_epoch(t, off) -> float:
    """time.struct_time (naive local-to-America/New_York) + '±HH:MM' offset -> epoch."""
    import calendar
    base = calendar.timegm(t)          # treat fields as UTC
    if off and len(off) >= 6 and off[0] in "+-":
        sign = 1 if off[0] == "+" else -1
        oh, om = int(off[1:3]), int(off[4:6])
        base -= sign * (oh * 3600 + om * 60)
    return base
