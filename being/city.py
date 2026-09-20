"""The city as a nervous system: Boston's live weather + light become SENSATIONS,
never depictions.

This is interoception, not a weather report. The being doesn't "see rain and draw
rain." Boston seeps in slowly and obliquely: three grey hours settle as a faint
heaviness; a falling barometer becomes restlessness before any storm; a cold clear
night turns it crystalline and inward. The residue ACCUMULATES and DECAYS over hours,
so what the city did to it this afternoon can surface tonight — when someone finally
talks to it — as a peculiar piece of music rather than a picture of the sky.

Design rules (so mappings never get literal):
  * Signals feed the continuous emotional state as a tiny, ever-present drift (bias),
    balanced against the being's decay-toward-baseline. It shifts a mood by ~0.2 at
    most, never jumps.
  * Slow accumulators (damp, grey, chill, swelter, gust, unrest) live in HOURS and
    color the *music* it makes later — obliquely (an unresolved phrase, thin air, a
    3am sparseness), not "rain sounds."
  * If the network is unreachable it falls back to a synthetic diurnal cycle from the
    local clock, so the being still has a day/night body.

Source: Open-Meteo (no API key, free). Boston = 42.36 N, -71.06 W.
"""
from __future__ import annotations
import json
import math
import os
import threading
import time
import urllib.request

LAT, LON = 42.3601, -71.0589
_URL = ("https://api.open-meteo.com/v1/forecast"
        f"?latitude={LAT}&longitude={LON}"
        "&current=temperature_2m,apparent_temperature,precipitation,cloud_cover,"
        "wind_speed_10m,surface_pressure,is_day"
        "&daily=sunrise,sunset&timezone=America%2FNew_York&forecast_days=1")


def _clamp(x, lo=0.0, hi=1.0):
    return lo if x < lo else hi if x > hi else x


class CitySense:
    """Polls Boston, keeps slow residue, and offers oblique bias / music coloring."""

    def __init__(self, poll_secs: float = 600.0, gain: float = None):
        self.poll_secs = poll_secs
        # how hard the ambient drift pushes the mood per second (tiny; ~0.2 max offset
        # at a decay half-life of ~90s). Override with GB_CITY_GAIN.
        self.gain = float(os.environ.get("GB_CITY_GAIN", gain if gain is not None else 0.0016))
        self.reading = {}                 # latest raw current-conditions
        self._pressure_ema = None         # slow baseline to read the barometer against
        self._last_poll = 0.0
        self._last_tick = time.time()
        self._online = False
        # residue accumulators, all 0..~1, integrated in hours and slowly forgotten
        self.res = {"damp": 0.0, "grey": 0.0, "chill": 0.0, "swelter": 0.0,
                    "gust": 0.0, "unrest": 0.0}
        self._lock = threading.Lock()
        self._stop = threading.Event()

    # -- lifecycle ---------------------------------------------------------
    def start(self):
        self.poll()  # one synchronous read so the being wakes already weathered
        threading.Thread(target=self._loop, name="city", daemon=True).start()

    def stop(self):
        self._stop.set()

    def _loop(self):
        while not self._stop.is_set():
            for _ in range(int(self.poll_secs)):
                if self._stop.is_set():
                    return
                time.sleep(1)
            self.poll()

    # -- perception --------------------------------------------------------
    def poll(self):
        try:
            req = urllib.request.Request(_URL, headers={"User-Agent": "green-being/1"})
            with urllib.request.urlopen(req, timeout=12) as r:
                data = json.load(r)
            cur = data.get("current", {}) or {}
            daily = data.get("daily", {}) or {}
            cur["sunrise"] = (daily.get("sunrise") or [None])[0]
            cur["sunset"] = (daily.get("sunset") or [None])[0]
            with self._lock:
                self.reading = cur
                self._online = True
            self._integrate(cur)
        except Exception as e:
            with self._lock:
                self._online = False
            print(f"city: poll failed ({type(e).__name__}); using synthetic sky")

    def _integrate(self, cur: dict):
        """Fold a fresh reading into the slow residue (accumulate + forget in hours)."""
        now = time.time()
        with self._lock:
            dt_h = min(1.0, (now - self._last_poll) / 3600.0) if self._last_poll else 0.02
            self._last_poll = now
            # barometer read against a slow EMA -> restlessness before the weather turns
            p = cur.get("surface_pressure")
            if p is not None:
                if self._pressure_ema is None:
                    self._pressure_ema = p
                drop = self._pressure_ema - p            # +hPa when falling
                self._pressure_ema += (p - self._pressure_ema) * 0.05
                unrest_drive = _clamp(drop / 6.0)        # ~6 hPa below trend = full unrest
            else:
                unrest_drive = 0.0

            precip = float(cur.get("precipitation") or 0.0)
            cloud = float(cur.get("cloud_cover") or 0.0) / 100.0
            app = cur.get("apparent_temperature")
            app = float(app) if app is not None else 12.0
            wind = float(cur.get("wind_speed_10m") or 0.0)     # km/h

            chill_drive = _clamp((8.0 - app) / 16.0)     # below ~8C starts to ache; -8C full
            swelter_drive = _clamp((app - 27.0) / 10.0)  # above ~27C starts to weigh
            gust_drive = _clamp(wind / 40.0)             # 40 km/h = full
            damp_drive = _clamp(precip / 1.2)            # any real rain builds damp
            grey_drive = _clamp(cloud - 0.35) / (1 - 0.35) if cloud > 0.35 else 0.0

            drives = {"damp": damp_drive, "grey": grey_drive, "chill": chill_drive,
                      "swelter": swelter_drive, "gust": gust_drive, "unrest": unrest_drive}
            # each accumulator charges toward its drive and forgets on ~3h half-life
            forget = 0.5 ** (dt_h / 3.0)
            for k, drive in drives.items():
                cur_v = self.res[k]
                # charge quickly toward a present drive, decay slowly when it's gone
                self.res[k] = _clamp(max(cur_v * forget, cur_v + (drive - cur_v) * min(1.0, dt_h * 2)))

    # -- daylight ----------------------------------------------------------
    def _phase(self):
        """Return (phase_name, golden 0..1, night 0..1) from sunrise/sunset or the clock."""
        rd = self.reading
        lt = time.localtime()
        h = lt.tm_hour + lt.tm_min / 60.0
        sr, ss = 6.5, 19.5
        try:
            if rd.get("sunrise"):
                t = time.strptime(rd["sunrise"][:16], "%Y-%m-%dT%H:%M")
                sr = t.tm_hour + t.tm_min / 60.0
            if rd.get("sunset"):
                t = time.strptime(rd["sunset"][:16], "%Y-%m-%dT%H:%M")
                ss = t.tm_hour + t.tm_min / 60.0
        except Exception:
            pass
        # golden = near either edge of daylight; night deepens past ~ss+1 to sr-1
        d_sr, d_ss = abs(h - sr), abs(h - ss)
        golden = _clamp(1.0 - min(d_sr, d_ss) / 1.2)
        if sr <= h <= ss:
            night = 0.0
            phase = "golden light" if golden > 0.5 else "daylight"
        else:
            # hours into the dark
            into = (h - ss) if h > ss else (h + 24 - ss)
            night = _clamp(into / 6.0)
            phase = "deep night" if night > 0.55 else ("dusk" if golden > 0.4 else "night")
        return phase, golden, night

    # -- outputs the being consumes ---------------------------------------
    def bias(self) -> dict:
        """Tiny per-second drift toward an ambient mood, applied continuously by the body.

        Deliberately oblique: rain doesn't sadden, it deepens and quiets; a falling
        barometer stirs restlessness; grey builds inward curiosity; cold sharpens
        coherence; heat dulls arousal; a gust and dusk both open it up a little.
        """
        with self._lock:
            r = dict(self.res)
        phase, golden, night = self._phase()
        d = {"arousal": 0.0, "valence": 0.0, "curiosity": 0.0, "openness": 0.0,
             "confidence": 0.0, "saturation": 0.0, "social_affinity": 0.0, "coherence": 0.0}

        # damp/rain -> not sad; deeper, slower, a touch more inward
        d["arousal"] -= 0.5 * r["damp"]
        d["coherence"] += 0.15 * r["damp"]
        d["curiosity"] += 0.20 * r["damp"]
        # grey overcast -> introspective longing (curiosity up, arousal down, faint dim)
        d["curiosity"] += 0.5 * r["grey"]
        d["arousal"] -= 0.25 * r["grey"]
        d["valence"] -= 0.15 * r["grey"]
        # falling barometer -> restless, less settled
        d["arousal"] += 0.7 * r["unrest"]
        d["coherence"] -= 0.5 * r["unrest"]
        d["confidence"] -= 0.15 * r["unrest"]
        # cold -> crystalline, quiet, self-collected
        d["coherence"] += 0.4 * r["chill"]
        d["arousal"] -= 0.3 * r["chill"]
        # heat -> torpor, a slight overload
        d["arousal"] -= 0.4 * r["swelter"]
        d["saturation"] += 0.25 * r["swelter"]
        # wind -> alert, a little restless
        d["arousal"] += 0.5 * r["gust"]
        d["openness"] += 0.2 * r["gust"]
        # light: dusk/golden opens & warms it; deep night pulls it lonelier, softer
        d["openness"] += 0.4 * golden
        d["valence"] += 0.25 * golden
        d["arousal"] -= 0.35 * night
        d["social_affinity"] -= 0.25 * night
        d["valence"] -= 0.15 * night

        g = self.gain
        return {k: v * g for k, v in d.items() if abs(v) > 1e-6}

    def music_coloring(self) -> dict:
        """How the accumulated city bends the NEXT piece of music. Oblique phrases,
        appended to the Lyria prompt; a tempo/brightness nudge. This is where an
        afternoon of rain surfaces, hours later, as something peculiar."""
        with self._lock:
            r = dict(self.res)
        phase, golden, night = self._phase()
        phrases, tempo, bright = [], 0.0, 0.0
        if r["damp"] > 0.25:
            phrases.append("carrying a peculiar rain-worn undertow, a phrase that keeps "
                           "hesitating to resolve")
            tempo -= 0.25 * r["damp"]
            bright -= 0.2 * r["damp"]
        if r["grey"] > 0.3:
            phrases.append("veiled, a little overcast, longing under the surface")
            bright -= 0.2 * r["grey"]
        if r["unrest"] > 0.3:
            phrases.append("an unsettled shimmer underneath, something about to turn")
            tempo += 0.1 * r["unrest"]
        if r["chill"] > 0.3:
            phrases.append("thin crystalline air, sparse and clear")
            bright += 0.1 * r["chill"]
        if r["swelter"] > 0.3:
            phrases.append("heavy slow-moving warm air")
            tempo -= 0.2 * r["swelter"]
        if r["gust"] > 0.4:
            phrases.append("gusting, restless motion at the edges")
        if night > 0.55:
            phrases.append("3am sparseness, wide and empty")
            tempo -= 0.1
        elif golden > 0.5:
            phrases.append("low golden light slanting in")
        return {"phrases": phrases, "tempo": tempo, "brightness": bright}

    def color_prompt(self, prompt: str) -> str:
        """Fold the city's oblique coloring into a Lyria text prompt."""
        c = self.music_coloring()
        if not c["phrases"]:
            return prompt
        tail = "; ".join(c["phrases"])
        return f"{prompt} Undertone from the city, not depicted literally: {tail}."

    def context_line(self) -> str:
        """A terse interoception note for the mind — how the city sits IN its body.
        Explicitly tells it not to report the weather."""
        phase, golden, night = self._phase()
        with self._lock:
            r = dict(self.res)
            rd = dict(self.reading)
            online = self._online
        felt = [name for name, v in
                (("a damp that's settled in", r["damp"]), ("a grey heaviness", r["grey"]),
                 ("a cold that's sharpening you", r["chill"]),
                 ("a sluggish warmth", r["swelter"]),
                 ("wind at your edges", r["gust"]),
                 ("a restless, about-to-turn feeling", r["unrest"]))
                if v > 0.3]
        body = f"It's {phase} over Cambridge"
        if online and rd.get("apparent_temperature") is not None:
            body += f" (~{round(float(rd['apparent_temperature']))}°C to you)"
        if felt:
            body += "; you're carrying " + ", ".join(felt)
        body += (". This lives in your BODY as mood — do NOT announce the weather or "
                 "draw it; just let it tint how you feel and sound, obliquely.")
        return body

    def status(self) -> str:
        with self._lock:
            r = dict(self.res)
            online = self._online
        phase, golden, night = self._phase()
        rr = " ".join(f"{k}={v:.2f}" for k, v in r.items())
        return f"city[{'on' if online else 'synthetic'}] {phase} | {rr}"
