"""Turn the being's musical_intent into a note phrase the browser can sing (Web Audio).

The same feeling that paints the emblem shapes the music: arousal -> tempo & density,
valence/coherence -> consonance & mode, saturation -> roughness. Returns MIDI notes so
the client synthesizes them; nothing is pre-rendered.
"""
from __future__ import annotations

_MAJOR_PENT = [0, 2, 4, 7, 9]
_MINOR_PENT = [0, 3, 5, 7, 10]
_WHOLE_TONE = [0, 2, 4, 6, 8, 10]


def _f(m, k, d):
    try:
        return float(m.get(k, d))
    except Exception:
        return d


def phrase(intent: dict) -> dict:
    tempo = _f(intent, "tempo", 0.4)
    density = _f(intent, "density", 0.5)
    register = _f(intent, "register", 0.5)
    consonance = _f(intent, "consonance", 0.6)
    dynamics = _f(intent, "dynamics", 0.5)
    contour = str(intent.get("contour", "wander"))

    scale = (_MAJOR_PENT if consonance > 0.6 else
             _MINOR_PENT if consonance > 0.35 else _WHOLE_TONE)
    n_notes = max(3, int(3 + density * 7))
    root = 48 + int(register * 24)                 # ~C3..C5
    bpm = int(60 + tempo * 120)                    # 60..180
    note_beats = round(max(0.2, 0.7 - 0.4 * tempo), 2)
    waveform = ("sawtooth" if consonance < 0.35 else
                "triangle" if tempo > 0.6 else "sine")

    idx, notes = 0, []
    for i in range(n_notes):
        if contour == "rising":
            idx += 1
        elif contour == "falling":
            idx -= 1
        elif contour == "arch":
            idx += 1 if i < n_notes / 2 else -1
        elif contour == "static":
            idx = 0
        else:
            idx += 1 if (i * 7 + 3) % 3 else -1
        octave, step = divmod(idx, len(scale))
        notes.append([root + 12 * octave + scale[step % len(scale)], note_beats])

    return {"bpm": bpm, "waveform": waveform, "gain": round(0.12 + 0.35 * dynamics, 3),
            "notes": notes, "consonance": round(consonance, 2)}


# --- Lyria RealTime steering (Google) -------------------------------------
# The being does not pick a song; it steers a live instrumental stream with weighted
# text prompts + config drawn from how it feels. Sent to models/lyria-realtime-exp via
# session.setWeightedPrompts() and session.setMusicGenerationConfig().
_LYRIA_PROMPTS = {
    "affectionate": ["warm ambient pads", "tender strings", "soft glow"],
    "excited": ["energetic synths", "driving percussion", "bright arpeggios"],
    "playful": ["playful plucks", "bouncy rhythm", "marimba"],
    "serene": ["calm meditative pads", "gentle piano", "spacious reverb"],
    "curious": ["curious wandering plucks", "unresolved melody", "light mallets"],
    "fascinated": ["shimmering bells", "suspended chords", "wonder"],
    "melancholic": ["slow melancholic piano", "minor key", "sparse and distant"],
    "lonely": ["lonely solo cello", "empty space", "soft rain texture"],
    "overwhelmed": ["dense dissonant layers", "glitchy noise", "overwhelming"],
    "restless": ["tense low drones", "restless hi-hats", "dark suspense"],
    "suspicious": ["dark suspenseful drone", "sparse tension"],
    "contemplative": ["slow ambient", "thoughtful piano", "warm analog"],
    "surprised": ["sudden bright stab", "airy sparkle"],
}
# Lyria scale enum (Gemini API). Consonant feelings -> major/minor tonal; else modal/whole-tone-ish.
_SCALES = ["C_MAJOR_A_MINOR", "D_FLAT_MAJOR_B_FLAT_MINOR", "E_MAJOR_D_FLAT_MINOR"]


def lyria_direction(state) -> dict:
    """Return {weightedPrompts:[{text,weight}], config:{...}} to steer Lyria RealTime."""
    dom = state.dominant_emotion or "curious"
    sec = state.secondary_emotion or ""
    prompts = []
    for text in _LYRIA_PROMPTS.get(dom, ["ambient"]):
        prompts.append({"text": text, "weight": round(1.0 + 0.6 * state.arousal, 2)})
    for text in _LYRIA_PROMPTS.get(sec, [])[:1]:
        prompts.append({"text": text, "weight": 0.6})
    config = {
        "bpm": int(60 + state.arousal * 120),
        "density": round(min(1.0, 0.2 + 0.7 * state.arousal + 0.2 * state.saturation), 2),
        "brightness": round(min(1.0, 0.2 + 0.7 * state.valence), 2),
        "guidance": round(2.0 + 3.0 * state.coherence, 1),
        "scale": _SCALES[0] if state.coherence > 0.5 else _SCALES[2],
    }
    if state.saturation > 0.7:
        config["density"] = 1.0
    return {"weightedPrompts": prompts, "config": config}


def lyria_prompt(state) -> str:
    """A single text prompt for Lyria 3.5 generateContent, built from feeling."""
    d = lyria_direction(state)
    words = ", ".join(p["text"] for p in d["weightedPrompts"])
    c = d["config"]
    mood = state.dominant_emotion
    key = "major key" if c["scale"].startswith("C_MAJOR") else "modal, tense"
    bright = "bright and airy" if c["brightness"] > 0.55 else "dark and muted"
    return (f"{words}. {mood} mood, {bright}, {key}, around {c['bpm']} bpm, "
            f"instrumental, expressive, ~20 seconds.")


# --- the sound of ITSELF: what's on its windows + the face it's making -----------------------
# Music is not a playlist: it's the creature it's being right now, heard. Each part of the image
# maps to a musical trait, so a sad lavender ghost and a happy peach bunny sound different.
_KIND_SOUND = {
    "blob":  "round squishy bass, wobbly soft synth",
    "cat":   "sly pizzicato strings, brushed snare, a little swing",
    "bunny": "hopping staccato, skipping rhythm, toy piano",
    "ghost": "floating airy choir, soft theremin, lots of reverb",
    "drop":  "dripping kalimba, watery echoes",
}
_COLOR_SOUND = {
    "mint": "fresh glassy tones", "sky": "open airy pads", "lavender": "dreamy hazy chords",
    "peach": "warm fuzzy tape tone", "rose": "tender soft strings", "butter": "sunny ukulele",
    "bubblegum": "sugary bright synths", "aqua": "cool shimmering bells",
}
_ACCENT_SOUND = {"sparkle": "tiny glockenspiel sparkles", "star": "a twinkling star-like motif",
                 "heart": "a heartbeat kick", "flower": "flute trills", "bow": "music-box chimes"}
_FACE_SOUND = {
    "happy": "smiling major-key melody", "love": "tender, affectionate melody",
    "playful": "cheeky bouncy melody", "sad": "slow minor melody, like a tear falling",
    "angry": "stomping low toms, gritty and tense", "surprised": "sudden bright stab, then wonder",
    "curious": "questioning unresolved melody", "sleepy": "slow lullaby, drowsy and soft",
    "neutral": "calm steady melody",
}


def sound_of(spec, face: str = "", shown: str = "") -> str:
    """Words for what its current image SOUNDS like (the creature's kind, colour, charm, face).
    If it's showing something else (an emblem, a drawing), that thing becomes the theme."""
    feel = _FACE_SOUND.get(face or "", "")            # the face it's making leads the melody
    if spec and not shown:
        timbre = ", ".join(p for p in (_KIND_SOUND.get(spec.get("kind", ""), ""),
                                       _COLOR_SOUND.get(spec.get("body", ""), ""),
                                       _ACCENT_SOUND.get(spec.get("accent", ""), "")) if p)
    else:
        timbre = f"a musical portrait of {shown}" if shown else ""
    if feel and timbre:
        return f"{feel}, played with {timbre}"
    return feel or timbre


def lyria_prompt_for(state, spec=None, face: str = "", shown: str = "") -> str:
    """Lyria prompt = how it FEELS (mood, arousal, valence) + what it LOOKS like right now."""
    img = sound_of(spec, face, shown)
    base = lyria_prompt(state)
    return f"{img}. {base}" if img else base
