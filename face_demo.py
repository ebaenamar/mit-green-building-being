#!/usr/bin/env python3
"""Showcase the being's face and its expressions on an instance.

  python3 face_demo.py witty-koala https://sundai.willsarg.com/api
"""
import sys, time, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from gbsim import WebDisplay, Color
from being.render import draw_face, ROWS, COLS

EXPRESSIONS = [
    ("happy",      dict(valence=.85, arousal=.5, curiosity=.4, saturation=.0)),
    ("curious",    dict(valence=.6, arousal=.55, curiosity=.85, saturation=.0)),
    ("surprised",  dict(valence=.6, arousal=.85, curiosity=.7, saturation=.1)),
    ("angry",      dict(valence=.3, arousal=.75, curiosity=.4, saturation=.2)),
    ("sad",        dict(valence=.22, arousal=.25, curiosity=.3, saturation=.1)),
    ("overwhelmed",dict(valence=.35, arousal=.7, curiosity=.4, saturation=.8)),
    ("serene",     dict(valence=.65, arousal=.3, curiosity=.45, saturation=.0)),
]


def to_frame(disp, buf):
    f = disp.makeframe()
    b = np.clip(buf, 0, 1)
    for r in range(ROWS):
        for c in range(COLS):
            f[r][c] = Color(int(b[r, c, 0]*255), int(b[r, c, 1]*255), int(b[r, c, 2]*255))
    return f


def main():
    name = sys.argv[1]
    base = next((a for a in sys.argv[2:] if a.startswith("http")), "http://localhost:8787/api")
    disp = WebDisplay(name, base_url=base)
    buf = np.zeros((ROWS, COLS, 3))
    print(f"Faces on '{name}'. Watch: {base.rsplit('/api',1)[0]}/{name}")
    t = 0.0
    while True:
        for label, emo in EXPRESSIONS:
            print("  face:", label)
            for _ in range(int(2.6 * 30)):     # ~2.6s each, with a blink
                draw_face(buf, emo, t)
                disp.send(to_frame(disp, buf))
                t += 1/30
                time.sleep(1/30)


if __name__ == "__main__":
    main()
