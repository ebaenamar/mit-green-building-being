#!/usr/bin/env python3
"""Show emblems INVENTED live from interactions (state + words). -> invent.html"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from being.state import EmotionalState
from being.perception import Perceiver
from being.memory import Memory
from being.mind import ReflexMind
from being.glyph import render_glyph, mood_tint, ROWS, COLS
from being.inventor import invent

STIMULI = [
    "hello, you are so beautiful tonight",
    "let's play! run run run!!!",
    "i wonder what the sea is hiding",
    "DANGER! something is chasing us!!!",
    "i feel so alone in the cold dark",
    "a little bird flew past, so curious",
    "i missed you, i finally came back",
    "STOP so loud too many voices!!!",
]
NF = 30


def react(stim):
    m = ReflexMind(); mem = Memory("/tmp/inv.json"); p = Perceiver()
    st = EmotionalState(); sens = p.perceive(stim)
    for _ in range(4):
        d = m.interpret(st, [sens], mem); st.approach(d.emotion_target, rate=0.6)
    name, glyph = invent(st, words=sens.words)
    return st, name, glyph


def frames(glyph, tint):
    out = []
    for i in range(NF):
        buf = np.zeros((ROWS, COLS, 3)); render_glyph(buf, glyph, i/12.0, tint)
        b = (np.clip(buf, 0, 1)*255).astype(int)
        out.append([[[int(b[r, c, 0]), int(b[r, c, 1]), int(b[r, c, 2])]
                     for c in range(COLS)] for r in range(ROWS)])
    return out


def main():
    cards, data = [], {}
    for stim in STIMULI:
        st, name, glyph = react(stim)
        data[name] = frames(glyph, mood_tint(st))
        cards.append((stim, name, f"{st.dominant_emotion}/{st.secondary_emotion}"))
    tiles = "".join(
        f'<figure><canvas id="c_{i}" width="{COLS*18}" height="{ROWS*18}"></canvas>'
        f'<figcaption><b>{html(nm)}</b><br><span class=e>{html(em)}</span>'
        f'<br><span class=s>“{html(stim)}”</span></figcaption></figure>'
        for i, (stim, nm, em) in enumerate(cards))
    doc = f"""<!doctype html><meta charset=utf8><title>invented emblems</title>
<style>body{{background:#0b0d13;color:#e6e8ef;font:13px -apple-system,sans-serif;margin:0;padding:24px}}
h1{{font-size:20px;margin:0 0 4px}}p{{color:#8b93a7;margin:0 0 18px}}
.grid{{display:flex;flex-wrap:wrap;gap:18px}}figure{{margin:0;width:170px;text-align:center}}
canvas{{background:#000;border-radius:8px;image-rendering:pixelated}}
figcaption{{margin-top:6px;color:#dfe4f0}}.e{{color:#7cc4ff}}.s{{color:#8b93a7;font-size:11px}}</style>
<h1>Emblems invented live from interaction</h1>
<p>Not chosen from a list — mutated & fused from the feeling and the words. Note the hybrids (nameXname).</p>
<div class="grid">{tiles}</div>
<script>const D={json.dumps(list(data.values()))};const S=18;
D.forEach((f,i)=>{{const x=document.getElementById('c_'+i).getContext('2d');let k=0;
setInterval(()=>{{const g=f[k%f.length];for(let r=0;r<g.length;r++)for(let c=0;c<g[0].length;c++){{
const p=g[r][c];x.fillStyle=`rgb(${{p[0]}},${{p[1]}},${{p[2]}})`;x.fillRect(c*S,r*S,S-1,S-1);}}k++;}},83);}});</script>"""
    open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "invent.html"), "w").write(doc)
    print("wrote invent.html |", len(cards), "invented:", ", ".join(d for _, d, _ in cards))


def html(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


if __name__ == "__main__":
    main()
