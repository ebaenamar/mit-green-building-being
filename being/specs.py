"""A seed library of glyphs written in the DSL (see glyph.py).

These double as few-shot examples for the AI: given the current feeling it can
return a glyph in exactly this shape, either reusing one of these or composing a
brand-new symbol from the same primitives.
"""

GLYPHS = {
    "sun": {
        "bg": "#0b0a1e", "bg_top": "#2a1a4a",
        "layers": [
            {"type": "rays", "cx": 4, "cy": 8, "count": 12, "len": 4, "spin": 0.7, "color": "#ff9a1f"},
            {"type": "disc", "cx": 4, "cy": 8, "r": 2.7, "color": "#fff6c8", "edge": "#ffc93c", "anim": "pulse"},
        ]},
    "moon": {
        "bg": "#05060f", "bg_top": "#0a0e24",
        "layers": [
            {"type": "particles", "n": 8, "color": "#cbd6ff", "motion": "swirl", "anim": "twinkle"},
            {"type": "crescent", "cx": 4, "cy": 8, "r": 3.6, "offset": 2.3, "color": "#eaf0ff"},
        ]},
    "heart": {
        "bg": "#0a0410",
        "layers": [
            {"type": "disc", "cx": 2.6, "cy": 6, "r": 1.9, "color": "#ff2d55", "anim": "pulse", "anim_amt": 1.4},
            {"type": "disc", "cx": 5.4, "cy": 6, "r": 1.9, "color": "#ff2d55", "anim": "pulse", "anim_amt": 1.4},
            {"type": "tri", "pts": [[0.8, 6.6], [7.2, 6.6], [4, 12.5]], "color": "#ff2d55", "anim": "pulse", "anim_amt": 1.4},
            {"type": "disc", "cx": 2.0, "cy": 5.3, "r": 0.7, "color": "#ff8fa8"},
        ]},
    "fire": {
        "bg": "#0a0402",
        "layers": [
            {"type": "flame", "cx": 4, "height": 12, "width": 4.6},
            {"type": "particles", "n": 4, "color": "#ffd23f", "motion": "rise", "speed": 6},
        ]},
    "star": {
        "bg": "#05060f", "bg_top": "#0a0e24",
        "layers": [
            {"type": "rays", "cx": 4, "cy": 8, "count": 5, "len": 5, "spin": 0.4, "color": "#ffe070"},
            {"type": "rays", "cx": 4, "cy": 8, "count": 5, "len": 2.4, "spin": 0.4, "color": "#fff6c8"},
            {"type": "disc", "cx": 4, "cy": 8, "r": 1.2, "color": "#ffffff", "anim": "pulse"},
        ]},
    "tree": {
        "bg": "#0c1406", "bg_top": "#16240c",
        "layers": [
            {"type": "rect", "x": 3.5, "y": 11, "w": 2, "h": 5, "color": "#5a2d00"},
            {"type": "disc", "cx": 4, "cy": 7, "r": 3.2, "color": "#1a9300", "edge": "#085a00", "anim": "sway", "anim_amt": 0.6},
            {"type": "disc", "cx": 2.4, "cy": 8.5, "r": 1.8, "color": "#1a9300"},
            {"type": "disc", "cx": 5.6, "cy": 8.5, "r": 1.8, "color": "#1a9300"},
        ]},
    "flower": {
        "bg": "#0c1406", "bg_top": "#123a2a",
        "layers": [
            {"type": "rect", "x": 3.7, "y": 11, "w": 1, "h": 5, "color": "#1a9300"},
            {"type": "disc", "cx": 4, "cy": 4, "r": 1.6, "color": "#ff4d8d", "anim": "pulse"},
            {"type": "disc", "cx": 1.8, "cy": 5.5, "r": 1.4, "color": "#ff8fc0"},
            {"type": "disc", "cx": 6.2, "cy": 5.5, "r": 1.4, "color": "#ff8fc0"},
            {"type": "disc", "cx": 2.6, "cy": 8, "r": 1.4, "color": "#ff8fc0"},
            {"type": "disc", "cx": 5.4, "cy": 8, "r": 1.4, "color": "#ff8fc0"},
            {"type": "disc", "cx": 4, "cy": 6.5, "r": 1.3, "color": "#ffe070"},
        ]},
    "bird": {
        "bg": "#0a1226", "bg_top": "#1a3a6b",
        "layers": [
            {"type": "disc", "cx": 4, "cy": 8, "r": 1.3, "color": "#2a2a2a"},
            {"type": "tri", "pts": [[4, 8], [0, 5.5], [1, 9]], "color": "#3a3a3a", "anim": "sway", "anim_amt": 1.2},
            {"type": "tri", "pts": [[4, 8], [8, 5.5], [7, 9]], "color": "#3a3a3a", "anim": "sway", "anim_amt": 1.2},
        ]},
    "rain": {
        "bg": "#0c1018", "bg_top": "#1a2230",
        "layers": [
            {"type": "disc", "cx": 3, "cy": 6, "r": 1.8, "color": "#8892a8"},
            {"type": "disc", "cx": 5.4, "cy": 6, "r": 2.0, "color": "#9aa4ba"},
            {"type": "disc", "cx": 4, "cy": 5, "r": 1.6, "color": "#aab4c8"},
            {"type": "particles", "n": 14, "color": "#a8c8ff", "motion": "fall", "speed": 7},
        ]},
    "spiral": {
        "bg": "#100a1e",
        "layers": [
            {"type": "particles", "n": 16, "color": "#c9a7ff", "motion": "swirl", "anim": "twinkle"},
            {"type": "ring", "cx": 4, "cy": 8, "r": 3.2, "thickness": 1, "color": "#8a5cff", "anim": "pulse"},
            {"type": "ring", "cx": 4, "cy": 8, "r": 1.6, "thickness": 1, "color": "#c9a7ff"},
        ]},
    "key": {
        "bg": "#0a0a0f",
        "layers": [
            {"type": "ring", "cx": 4, "cy": 4.5, "r": 2.0, "thickness": 1.2, "color": "#f0b838"},
            {"type": "line", "x1": 4, "y1": 6, "x2": 4, "y2": 14, "color": "#f0b838"},
            {"type": "rect", "x": 5, "y": 12, "w": 1.5, "h": 1, "color": "#f0b838"},
            {"type": "rect", "x": 5, "y": 13.5, "w": 2, "h": 1, "color": "#f0b838"},
        ]},
}

# which feeling reaches for which seed symbol (the AI may override or invent)
EMOTION_GLYPH = {
    "affectionate": "heart", "excited": "fire", "playful": "star", "serene": "sun",
    "curious": "key", "fascinated": "star", "melancholic": "moon", "lonely": "moon",
    "overwhelmed": "spiral", "restless": "fire", "suspicious": "moon",
    "contemplative": "tree", "surprised": "star",
}
