#!/usr/bin/env python3
"""Show the being transforming through a sequence of symbols. -> morph.html"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from being.glyph import ROWS, COLS
from being.morph import Expression
from being.specs import GLYPHS

SEQ = ["heart", "fire", "spiral", "moon", "star", "tree", "sun", "heart"]
HOLD, TRANS, FPS = 1.2, 1.3, 24


def main():
    ex = Expression()
    ex.set_glyph(GLYPHS[SEQ[0]])
    frames, t = [], 0.0
    for name in SEQ[1:]:
        for _ in range(int(HOLD * FPS)):          # hold current
            ex.update(1/FPS); buf = np.zeros((ROWS, COLS, 3)); ex.render(buf, t)
            frames.append(buf.copy()); t += 1/FPS
        ex.set_glyph(GLYPHS[name], dur=TRANS)      # begin transformation
        for _ in range(int(TRANS * FPS)):
            ex.update(1/FPS); buf = np.zeros((ROWS, COLS, 3)); ex.render(buf, t)
            frames.append(buf.copy()); t += 1/FPS

    data = []
    for buf in frames:
        b = (np.clip(buf, 0, 1)*255).astype(int)
        data.append([[[int(b[r, c, 0]), int(b[r, c, 1]), int(b[r, c, 2])]
                      for c in range(COLS)] for r in range(ROWS)])
    doc = f"""<!doctype html><meta charset=utf8><title>transformations</title>
<style>body{{background:#0b0d13;color:#e6e8ef;font:15px -apple-system,sans-serif;margin:0;
display:flex;flex-direction:column;align-items:center;padding:30px}}
h1{{font-size:20px}}canvas{{background:#000;border-radius:10px;image-rendering:pixelated;margin-top:10px}}
p{{color:#8b93a7}}</style>
<h1>Transformation periods — one feeling becoming the next</h1>
<p>heart → fire → spiral → moon → star → tree → sun → heart (dissolve with a spark frontier)</p>
<canvas id=cv width={COLS*28} height={ROWS*28}></canvas>
<script>const F={json.dumps(data)};const S=28,x=document.getElementById('cv').getContext('2d');let i=0;
setInterval(()=>{{const g=F[i%F.length];for(let r=0;r<g.length;r++)for(let c=0;c<g[0].length;c++){{
const p=g[r][c];x.fillStyle=`rgb(${{p[0]}},${{p[1]}},${{p[2]}})`;x.fillRect(c*S,r*S,S-1,S-1);}}i++;}},{int(1000/FPS)});</script>"""
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "morph.html")
    open(out, "w").write(doc)
    print("wrote", out, "|", len(frames), "frames")


if __name__ == "__main__":
    main()
