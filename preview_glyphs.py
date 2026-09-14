#!/usr/bin/env python3
"""Render every DSL glyph (being/specs.py) animated. -> glyphs.html"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from being.glyph import render_glyph, ROWS, COLS
from being.specs import GLYPHS

NF = 36


def frames_for(g):
    out = []
    for i in range(NF):
        buf = np.zeros((ROWS, COLS, 3))
        render_glyph(buf, g, i/12.0)
        b = (np.clip(buf, 0, 1)*255).astype(int)
        out.append([[[int(b[r, c, 0]), int(b[r, c, 1]), int(b[r, c, 2])]
                     for c in range(COLS)] for r in range(ROWS)])
    return out


def main():
    data = {n: frames_for(g) for n, g in GLYPHS.items()}
    tiles = "".join(
        f'<figure><canvas id="c_{n}" width="{COLS*20}" height="{ROWS*20}"></canvas>'
        f'<figcaption>{n}</figcaption></figure>' for n in data)
    doc = f"""<!doctype html><meta charset=utf8><title>glyph DSL</title>
<style>body{{background:#0b0d13;color:#e6e8ef;font:14px -apple-system,sans-serif;margin:0;padding:24px}}
h1{{font-size:20px;margin:0 0 4px}}p{{color:#8b93a7;margin:0 0 18px}}
.grid{{display:flex;flex-wrap:wrap;gap:18px}}figure{{margin:0;text-align:center}}
canvas{{background:#000;border-radius:8px;image-rendering:pixelated}}figcaption{{margin-top:6px;color:#c7cde0;font-size:12px}}</style>
<h1>Symbol DSL — composed from primitives (data, not code)</h1>
<p>Each of these is a small JSON recipe. The AI can return new ones in the same shape.</p>
<div class="grid">{tiles}</div>
<script>const D={json.dumps(data)};const S=20;
for(const n in D){{const cv=document.getElementById('c_'+n),x=cv.getContext('2d'),f=D[n];let i=0;
setInterval(()=>{{const g=f[i%f.length];for(let r=0;r<g.length;r++)for(let c=0;c<g[0].length;c++){{
const p=g[r][c];x.fillStyle=`rgb(${{p[0]}},${{p[1]}},${{p[2]}})`;x.fillRect(c*S,r*S,S-1,S-1);}}i++;}},83);}}</script>"""
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "glyphs.html")
    open(out, "w").write(doc)
    print("wrote", out, "|", len(data), "glyphs:", ", ".join(data))


if __name__ == "__main__":
    main()
