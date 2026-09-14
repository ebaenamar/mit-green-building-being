#!/usr/bin/env python3
"""Render every emblem as an animated tile so you can judge legibility. -> emblems.html"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from being import emblems as E

LABELS = {"fire": "FIRE · excitement / anger", "heart": "HEART · affection",
          "wave": "WAVE · overwhelmed", "sun": "SUN · joy / serenity",
          "moon": "MOON · melancholy", "eye": "EYE · curiosity / watching",
          "boat": "BOAT · journey / curiosity", "hand": "HAND · greeting / reaching"}
NFRAMES = 36


def frames_for(fn):
    out = []
    for i in range(NFRAMES):
        buf = np.zeros((E.ROWS, E.COLS, 3))
        fn(buf, i / 12.0, 1.0)
        b = (np.clip(buf, 0, 1) * 255).astype(int)
        out.append([[[int(b[r, c, 0]), int(b[r, c, 1]), int(b[r, c, 2])]
                     for c in range(E.COLS)] for r in range(E.ROWS)])
    return out


def main():
    data = {name: frames_for(fn) for name, fn in E.EMBLEMS.items()}
    tiles = "".join(
        f'<figure><canvas id="c_{n}" width="{E.COLS*20}" height="{E.ROWS*20}"></canvas>'
        f'<figcaption>{LABELS.get(n, n)}</figcaption></figure>' for n in data)
    doc = f"""<!doctype html><meta charset=utf8><title>Green Being — emblems</title>
<style>
 body{{background:#0b0d13;color:#e6e8ef;font:14px -apple-system,Segoe UI,sans-serif;margin:0;padding:26px}}
 h1{{font-size:21px;margin:0 0 4px}} p{{color:#8b93a7;margin:0 0 20px}}
 .grid{{display:flex;flex-wrap:wrap;gap:22px}}
 figure{{margin:0;text-align:center}} canvas{{background:#000;border-radius:8px;image-rendering:pixelated}}
 figcaption{{margin-top:8px;color:#c7cde0;font-size:12px}}
</style>
<h1>Green Being — emblem vocabulary</h1>
<p>Bold recognizable symbols, one per emotion. Animated at ~12 fps. This is the proposed visual language.</p>
<div class="grid">{tiles}</div>
<script>
const DATA={json.dumps(data)};
const S=20;
for(const name in DATA){{
  const cv=document.getElementById('c_'+name), ctx=cv.getContext('2d'), fr=DATA[name];
  let i=0;
  setInterval(()=>{{
    const g=fr[i%fr.length];
    for(let r=0;r<g.length;r++)for(let c=0;c<g[0].length;c++){{
      const p=g[r][c]; ctx.fillStyle=`rgb(${{p[0]}},${{p[1]}},${{p[2]}})`;
      ctx.fillRect(c*S,r*S,S-1,S-1);
    }}
    i++;
  }},83);
}}
</script>"""
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "emblems.html")
    open(out, "w").write(doc)
    print("wrote", out, "| emblems:", ", ".join(data))


if __name__ == "__main__":
    main()
