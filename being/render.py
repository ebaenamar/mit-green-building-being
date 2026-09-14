"""The visual body: a scrolling top-down Zelda-style overworld on the 17x9 grid.

The world is not decoration; it is how the being's feelings become visible.
Emotion picks the biome, the time of day, the weather, and what Link is doing:

    calm + pleasant      -> sunny green overworld, Link strolls the path
    affectionate         -> flowered meadow, hearts drift up
    curious              -> a cave / chest ahead, Link explores toward it
    aroused + tense      -> Octoroks appear, Link draws the sword, fast scroll
    melancholic / lonely -> night forest, rain, a single lantern glow
    overloaded           -> a cramped dungeon, walls close in, tiles glitch

NES overworld hex values (authentic): foliage #1A9300, sand path #F7D7A4,
water #4846FF, brown rock #995200, red rock #B4392A, ground #FFCBC4.
"""
from __future__ import annotations
import math

ROWS, COLS = 17, 9
LINK_ROW = 11          # Link sits low-centre; the world scrolls past him.


def hx(s: str):
    s = s.lstrip("#")
    return (int(s[0:2], 16) / 255.0, int(s[2:4], 16) / 255.0, int(s[4:6], 16) / 255.0)


# --- authentic-ish NES Zelda palette (RGB floats) ---------------------------
C = {
    "grass":    hx("1A9300"),
    "grass2":   hx("0E6B00"),   # darker grass speckle
    "foliage":  hx("085A00"),   # tree/bush canopy
    "trunk":    hx("5A2D00"),
    "path":     hx("F7D7A4"),   # sand trail
    "sand":     hx("E8C48A"),
    "water":    hx("4846FF"),
    "water2":   hx("68A8FF"),   # shimmer highlight
    "rock":     hx("995200"),
    "redrock":  hx("B4392A"),
    "ground":   hx("FFCBC4"),
    "flower":   hx("F84848"),
    "flower2":  hx("F8F858"),
    "link":     hx("00C800"),   # tunic, brighter than grass so he reads
    "link_dk":  hx("007800"),
    "skin":     hx("FCA044"),
    "sword":    hx("D8F8F8"),
    "heart":    hx("F82838"),
    "rupee":    hx("38C8F8"),
    "chest":    hx("F0B838"),
    "chest_dk": hx("8A5A10"),
    "wall":     hx("6A4A2A"),   # dungeon brick
    "floor":    hx("2A1E12"),
    "rain":     hx("A8C8FF"),
    "fire":     hx("FFE070"),   # firefly / lantern
    "night":    (0.05, 0.06, 0.16),
}

GRASS, FOLIAGE, PATH, WATER, ROCK, FLOWER, WALL, FLOOR = range(8)


def _h(x: int) -> int:
    x &= 0xFFFFFFFF
    x = (x ^ 61) ^ (x >> 16)
    x = (x + (x << 3)) & 0xFFFFFFFF
    x ^= (x >> 4)
    x = (x * 0x27D4EB2D) & 0xFFFFFFFF
    x ^= (x >> 15)
    return x & 0xFFFFFFFF


def noise(*ints: int) -> float:
    """Deterministic 0..1 pseudo-noise from integer coords (stable across runs)."""
    v = 0x9E3779B9
    for i in ints:
        v = _h(v * 1000003 + (int(i) & 0xFFFFFFFF))
    return (v & 0xFFFFFF) / float(0xFFFFFF)


def path_col(wrow: int) -> int:
    """A gently meandering vertical trail Link follows."""
    return int(round(4 + 2.2 * math.sin(wrow * 0.28) + 0.8 * math.sin(wrow * 0.11)))


def _tile(biome: str, col: int, wrow: int) -> int:
    pc = path_col(wrow)
    if biome == "dungeon":
        if col == 0 or col == COLS - 1:
            return WALL
        if noise(col, wrow, 71) > 0.86:
            return WALL
        return FLOOR
    if abs(col - pc) == 0:
        return PATH
    # coarse water bodies (2x2-ish patches), suppressed next to the path
    if biome != "cave" and noise(col // 2, wrow // 2, 13) > 0.86 and abs(col - pc) > 1:
        return WATER
    tree_thr = {"forest": 0.62, "night_forest": 0.66, "meadow": 0.86,
                "cave": 0.70, "action": 0.80}.get(biome, 0.78)
    if noise(col, wrow, 1) > tree_thr:
        return FOLIAGE
    if biome == "cave" and noise(col, wrow, 5) > 0.80:
        return ROCK
    if biome == "meadow" and noise(col, wrow, 2) > 0.84:
        return FLOWER
    if noise(col, wrow, 9) > 0.955:
        return ROCK
    return GRASS


def draw_face(buf, emo: dict, t: float):
    """A bold Link face filling the 17x9 grid. Expression comes from feeling:
    valence -> smile/frown, arousal -> eyes wide, curiosity -> gaze to the side,
    saturation -> a pained squint. The being wears this when it turns to look at you.
    """
    buf[:] = 0.0
    val = emo.get("valence", 0.5)
    ar = emo.get("arousal", 0.4)
    cu = emo.get("curiosity", 0.5)
    sat = emo.get("saturation", 0.0)

    skin = C["skin"]
    skin_dk = tuple(x * 0.78 for x in skin)
    cap = C["link"]
    cap_dk = C["link_dk"]
    hair = C["trunk"]
    white = (0.95, 0.95, 0.95)
    pupil = (0.05, 0.06, 0.14)
    mouth = (0.55, 0.06, 0.08)

    # head (skin oval)
    for r in range(ROWS):
        for c in range(COLS):
            dx, dy = (c - 4) / 3.5, (r - 9.5) / 6.8
            if dx * dx + dy * dy <= 1.0:
                _mix(buf, r, c, skin)
    # green cap over the crown
    for r in range(ROWS):
        for c in range(COLS):
            dx, dy = (c - 4) / 3.8, (r - 9.5) / 7.4
            if dx * dx + dy * dy <= 1.0 and r <= 4:
                _mix(buf, r, c, cap if r > 0 else cap_dk)
    for r in range(0, 4):                    # floppy hat tip
        _mix(buf, r, min(COLS - 1, 5 + r), cap)
    _mix(buf, 0, 4, cap)
    for c in range(2, 7):                     # bangs
        _mix(buf, 5, c, hair, 0.85)
    for r in (6, 7):                          # sideburns
        _mix(buf, r, 1, hair, 0.8)
        _mix(buf, r, 7, hair, 0.8)

    blink = (t % 3.4) < 0.14
    gaze = 1 if cu > 0.6 else (-1 if cu < 0.3 else 0)   # look aside when curious
    look_down = 1 if val < 0.35 else 0                   # eyes droop when low
    er = 8 + look_down
    for (ex) in (2, 5):                        # two eyes (white)
        for c in (ex, ex + 1):
            if blink:
                _mix(buf, er, c, skin_dk)      # closed: a lash line
            else:
                _mix(buf, er, c, white)
                _mix(buf, er + 1, c, white) if ar > 0.55 else None   # wide eyes
        if not blink:
            _mix(buf, er, ex + (1 if gaze >= 0 else 0), pupil)  # pupil
            _mix(buf, er, min(ex + 1, ex + 1) if gaze > 0 else ex, pupil)

    # eyebrows: raised when surprised, angled down when angry/overloaded
    brow = 6 if (ar > 0.6 and val > 0.4) else 7
    if sat > 0.55 or (ar > 0.55 and val < 0.4):   # tense/angry: inner-down slant
        _mix(buf, 7, 3, hair); _mix(buf, 6, 2, hair)
        _mix(buf, 7, 5, hair); _mix(buf, 6, 6, hair)
    else:
        for c in (2, 3):
            _mix(buf, brow, c, hair, 0.8)
        for c in (5, 6):
            _mix(buf, brow, c, hair, 0.8)

    _mix(buf, 11, 4, skin_dk)                  # nose

    # mouth
    if sat > 0.6:                              # gritted / pained
        for c in (3, 4, 5):
            _mix(buf, 13, c, mouth)
        _mix(buf, 12, 4, mouth, 0.5)
    elif ar > 0.7 and cu > 0.5:               # surprise: open O
        _mix(buf, 12, 4, mouth); _mix(buf, 14, 4, mouth)
        _mix(buf, 13, 3, mouth); _mix(buf, 13, 5, mouth)
    elif val > 0.58:                          # smile
        _mix(buf, 13, 3, mouth); _mix(buf, 13, 5, mouth)
        _mix(buf, 14, 4, mouth)
        if val > 0.75:
            _mix(buf, 14, 3, mouth); _mix(buf, 14, 5, mouth)
    elif val < 0.4:                           # frown
        _mix(buf, 14, 3, mouth); _mix(buf, 14, 5, mouth)
        _mix(buf, 13, 4, mouth)
    else:                                     # neutral
        for c in (3, 4, 5):
            _mix(buf, 13, c, mouth)

    glow = 1.0 + 0.25 * ar + 0.15 * (val - 0.5)   # brighter when roused/happy
    buf *= max(0.6, glow)


def _mix(buf, r, c, color, a=1.0):
    if 0 <= r < ROWS and 0 <= c < COLS and a > 0:
        ia = 1.0 - a
        buf[r, c, 0] = buf[r, c, 0] * ia + color[0] * a
        buf[r, c, 1] = buf[r, c, 1] * ia + color[1] * a
        buf[r, c, 2] = buf[r, c, 2] * ia + color[2] * a


_BIOMES = {"overworld", "meadow", "forest", "night_forest", "cave", "action", "dungeon"}


def _pick_biome(s) -> str:
    if s.saturation > 0.6:
        return "dungeon"                                    # overload
    if s.arousal > 0.62 and s.valence < 0.5:
        return "action"                                     # roused + wary/afraid
    if s.valence < 0.36 and s.arousal < 0.5:
        return "night_forest"                               # melancholy / lonely
    if s.social_affinity > 0.55 and s.valence > 0.6:
        return "meadow"                                     # affectionate
    if s.curiosity > 0.58 and s.valence >= 0.4:
        return "cave"                                       # curious seeking
    if s.arousal > 0.6 and s.valence >= 0.6:
        return "meadow"                                     # excited joy, lively
    if s.curiosity > 0.5:
        return "forest"
    return "overworld"


class ZeldaWorld:
    """A living overworld the being scrolls through as it feels its way through the day."""

    def __init__(self, time_of_day: float = 0.5):
        self.scroll = 0.0
        self.link_c = 4.0
        self.biome = "overworld"
        self.night = 0.0
        self.rain = 0.0
        self.speed = 1.5
        self.walk_phase = 0.0
        self.sword = 0.0            # 0..1 how drawn the sword is
        self.time_of_day = time_of_day
        self.entities = []          # hearts, rupees, enemies, chest, sparkles
        self.rain_drops = []
        self.fireflies = []
        self._flash = 0.0
        self.face_timer = 0.0       # seconds the being holds eye contact
        self.emo = {}               # last emotional snapshot, for the face
        self._spawn_cd = {"enemy": 0.0, "heart": 0.0, "rupee": 0.0}
        for _ in range(6):
            self.fireflies.append([noise(_, 3) * COLS, noise(_, 7) * ROWS,
                                   0.3 + noise(_, 9)])

    # -- reflex: the instant "I noticed you" spark -------------------------
    def flash(self):
        self._flash = 1.0
        self.entities.append({"kind": "spark", "r": LINK_ROW - 1.0,
                              "c": self.link_c, "ttl": 0.5, "vy": -3.0})

    def look(self, seconds: float = 4.0):
        """Turn to face whoever spoke — hold eye contact for a few seconds."""
        self.face_timer = max(self.face_timer, seconds)

    def wrow(self, r: int) -> int:
        return int(self.scroll) + (ROWS - 1 - r)

    # -- drive the world from feeling --------------------------------------
    def update(self, s, hint: dict, dt: float):
        self.emo = {k: getattr(s, k) for k in
                    ("valence", "arousal", "curiosity", "openness", "confidence",
                     "saturation", "social_affinity", "coherence")}
        self.face_timer = max(0.0, self.face_timer - dt)
        scene = (hint or {}).get("scene")
        if scene == "face":
            self.face_timer = max(self.face_timer, 0.2)
        self.biome = scene if scene and scene in _BIOMES else _pick_biome(s)
        # day/night: internal clock plus mood (melancholy darkens, joy brightens)
        clock_night = 0.5 + 0.5 * math.cos(self.time_of_day * 2 * math.pi)
        self.night = max(0.0, min(1.0, 0.55 * clock_night + 0.55 * (1 - s.valence)
                                  - 0.25 * s.arousal))
        if self.biome in ("night_forest", "dungeon", "cave"):
            self.night = max(self.night, 0.55)
        self.rain += ((1.0 if (s.valence < 0.42 and s.arousal < 0.55) else 0.0) - self.rain) * min(1, dt * 0.5)
        self.speed = 0.6 + 5.5 * s.arousal
        self.sword += ((1.0 if (s.arousal > 0.6 and s.confidence > 0.45) else 0.0) - self.sword) * min(1, dt * 3)

        self.scroll += self.speed * dt
        self.walk_phase = (self.walk_phase + self.speed * dt * 1.6) % 1.0
        target_c = path_col(self.wrow(LINK_ROW))
        self.link_c += (target_c - self.link_c) * min(1.0, dt * 4.0)

        self._advance_entities(s, dt)
        if self._flash > 0:
            self._flash = max(0.0, self._flash - dt * 2.5)

    def _advance_entities(self, s, dt):
        for k in self._spawn_cd:
            self._spawn_cd[k] = max(0.0, self._spawn_cd[k] - dt)

        # Octoroks when roused and wary; hearts when affectionate; rupees when curious.
        want_enemy = s.arousal * (1 - s.valence)
        if want_enemy > 0.35 and self._spawn_cd["enemy"] <= 0 and len(
                [e for e in self.entities if e["kind"] == "enemy"]) < 3:
            self.entities.append({"kind": "enemy", "r": -1.0,
                                  "c": 1 + noise(int(self.scroll), 4) * (COLS - 2),
                                  "vy": 2.0 + 3 * s.arousal, "phase": 0.0, "ttl": 8.0})
            self._spawn_cd["enemy"] = 1.6 - want_enemy
        if s.social_affinity * s.valence > 0.4 and self._spawn_cd["heart"] <= 0:
            self.entities.append({"kind": "heart", "r": LINK_ROW + 0.5,
                                  "c": self.link_c + (noise(int(self.scroll * 7), 2) - 0.5) * 2,
                                  "vy": -2.5, "ttl": 2.2})
            self._spawn_cd["heart"] = 1.4
        if s.curiosity > 0.55 and self._spawn_cd["rupee"] <= 0:
            self.entities.append({"kind": "rupee", "r": -0.5,
                                  "c": 1 + noise(int(self.scroll), 8) * (COLS - 2),
                                  "vy": self.speed * 0.9, "phase": 0.0, "ttl": 9.0})
            self._spawn_cd["rupee"] = 2.2
        if self.biome == "cave" and not any(e["kind"] == "chest" for e in self.entities):
            self.entities.append({"kind": "chest", "r": -1.0, "c": path_col(self.wrow(0)),
                                  "vy": self.speed, "ttl": 30.0, "open": 0.0})

        alive = []
        for e in self.entities:
            e["ttl"] -= dt
            if e["kind"] in ("enemy", "rupee", "chest"):
                e["r"] += e.get("vy", self.speed) * dt          # scroll toward Link
                if e["kind"] == "enemy":
                    e["c"] += math.sin((e.setdefault("phase", 0.0)) ) * dt * 2
                    e["phase"] += dt * 3
                if e["kind"] == "chest" and abs(e["r"] - LINK_ROW) < 1.2:
                    e["open"] = min(1.0, e.get("open", 0.0) + dt * 2)
            elif e["kind"] in ("heart", "spark"):
                e["r"] += e.get("vy", -2.0) * dt
            if e["ttl"] > 0 and -2 <= e["r"] <= ROWS + 1:
                alive.append(e)
        self.entities = alive

        for f in self.fireflies:
            f[0] += math.sin(self.walk_phase * 6.28 + f[1]) * dt * 0.6
            f[1] += math.cos(self.walk_phase * 6.28 + f[0]) * dt * 0.6
            f[0] %= COLS
            f[1] %= ROWS

    # -- paint one frame ----------------------------------------------------
    def _tile_color(self, kind: int, col: int, wrow: int, t: float):
        if kind == GRASS:
            return C["grass2"] if noise(col, wrow, 21) > 0.82 else C["grass"]
        if kind == FOLIAGE:
            return C["foliage"]
        if kind == PATH:
            return C["path"]
        if kind == WATER:
            shimmer = (math.sin(t * 3 + col * 1.3 + wrow * 0.7) + 1) * 0.5
            return C["water2"] if shimmer > 0.7 else C["water"]
        if kind == ROCK:
            return C["redrock"] if self.biome in ("cave", "action") else C["rock"]
        if kind == FLOWER:
            return C["flower2"] if noise(col, wrow, 33) > 0.5 else C["flower"]
        if kind == WALL:
            return C["wall"]
        return C["floor"]

    def render(self, buf, t: float):
        if self.face_timer > 0:
            draw_face(buf, self.emo, t)
            if self._flash > 0:
                buf *= (1.0 + 0.5 * self._flash)
            return
        buf[:] = 0.0
        # terrain
        for r in range(ROWS):
            wr = self.wrow(r)
            for c in range(COLS):
                _mix(buf, r, c, self._tile_color(_tile(self.biome, c, wr), c, wr, t))

        # rain streaks
        if self.rain > 0.15:
            n = int(self.rain * 10)
            for i in range(n):
                rc = int(noise(i, int(t * 12), 1) * COLS)
                rr = int((noise(i, 5) * ROWS + t * 14) % ROWS)
                _mix(buf, rr, rc, C["rain"], 0.5 * self.rain)

        # ground/floating entities
        for e in self.entities:
            r, c = int(round(e["r"])), int(round(e["c"]))
            k = e["kind"]
            if k == "enemy":
                _mix(buf, r, c, C["redrock"])
                _mix(buf, r, c, C["flower"], 0.5)   # a menacing red Octorok blob
            elif k == "rupee":
                tw = 0.6 + 0.4 * math.sin(t * 6 + c)
                _mix(buf, r, c, C["rupee"], tw)
            elif k == "heart":
                _mix(buf, r, c, C["heart"])
            elif k == "spark":
                _mix(buf, r, c, C["sword"], max(0.0, e["ttl"] * 2))
            elif k == "chest":
                _mix(buf, r, c, C["chest_dk"])
                _mix(buf, r, c, C["chest"], 0.6 + 0.4 * e.get("open", 0))

        # Link — a plus-shaped clearing so his tunic reads against foliage
        lr, lc = LINK_ROW, int(round(self.link_c))
        bob = -1 if (self.walk_phase > 0.5 and self.speed > 0.8) else 0
        _mix(buf, lr, lc, C["link_dk"], 0.35)          # soft shadow under him
        _mix(buf, lr + bob, lc, C["link"])
        _mix(buf, lr + bob - 1, lc, C["skin"], 0.9)    # head
        if self.sword > 0.4:
            _mix(buf, lr + bob, lc + 1, C["sword"], self.sword)

        # night tint + firefly/lantern glow
        if self.night > 0.02:
            n = self.night
            nb = C["night"]
            for r in range(ROWS):
                for c in range(COLS):
                    buf[r, c, 0] = buf[r, c, 0] * (1 - 0.75 * n) + nb[0] * n
                    buf[r, c, 1] = buf[r, c, 1] * (1 - 0.75 * n) + nb[1] * n
                    buf[r, c, 2] = buf[r, c, 2] * (1 - 0.6 * n) + nb[2] * n
            for f in self.fireflies:
                tw = (0.4 + 0.6 * math.sin(t * 4 + f[0] + f[1])) * f[2] * n
                _mix(buf, int(f[1]), int(f[0]), C["fire"], max(0.0, tw))

        # overload: brief horizontal tile glitching
        if self.biome == "dungeon" or self._flash < 0:
            pass
        # attention flash brightens the whole body for a beat
        if self._flash > 0:
            buf *= (1.0 + 0.6 * self._flash)

    def glitch(self, buf, amount: float, t: float):
        """Sensory-overload artifact: shove random rows sideways."""
        if amount <= 0.05:
            return
        for r in range(ROWS):
            if noise(r, int(t * 8), 2) < amount * 0.5:
                shift = 1 + int(noise(r, int(t * 8), 3) * 2)
                buf[r] = __import__("numpy").roll(buf[r], shift, axis=0)

