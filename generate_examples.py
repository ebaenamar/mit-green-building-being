#!/usr/bin/env python3
"""Generate a gallery of the being's emotional reactions and actions.

For each example stimulus (starting from a neutral rest each time), it runs
PERCEIVE -> mind -> EXPRESS and records the resulting emotional state, the
interpretation, the visual action (Zelda world + face, rendered to pixels) and
the musical action. Writes examples.html.

  OPENAI_API_KEY=... python3 generate_examples.py     # rich LLM interpretation
  python3 generate_examples.py                         # heuristic reflex mind
"""
import os, sys, html
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from being.state import EmotionalState
from being.perception import Perceiver
from being.memory import Memory
from being.mind import make_mind
from being.render import ZeldaWorld, draw_face, ROWS, COLS

STIMULI = [
    "hello there, you are so beautiful tonight",
    "let's play! run run run, jump and dance!!!",
    "i wonder what is hidden inside that dark cave...",
    "DANGER! something is chasing us, look out!!!",
    "i feel so alone in the cold empty dark",
    "STOP it's SO LOUD too many voices at once!!!",
    "shhh, rest now, be still and quiet with me",
    "i missed you so much, i finally came back",
]

SCALARS = ["arousal", "valence", "curiosity", "openness",
           "confidence", "saturation", "social_affinity", "coherence"]


def grid_html(buf, cell=15):
    b = np.clip(buf, 0, 1)
    cells = []
    for r in range(ROWS):
        for c in range(COLS):
            r8, g8, b8 = (int(b[r, c, 0]*255), int(b[r, c, 1]*255), int(b[r, c, 2]*255))
            cells.append(f'<div style="background:rgb({r8},{g8},{b8})"></div>')
    return (f'<div class="grid" style="grid-template-columns:repeat({COLS},{cell}px);'
            f'grid-auto-rows:{cell}px">{"".join(cells)}</div>')


def bars_html(state):
    rows = []
    for k in SCALARS:
        v = getattr(state, k)
        rows.append(
            f'<div class="bar"><span class="k">{k}</span>'
            f'<span class="track"><i style="width:{v*100:.0f}%"></i></span>'
            f'<span class="v">{v:.2f}</span></div>')
    return "".join(rows)


def render_world(state):
    w = ZeldaWorld(time_of_day=0.95 if state.valence < 0.4 and state.arousal < 0.5 else 0.5)
    buf = np.zeros((ROWS, COLS, 3))
    for _ in range(60):
        w.update(state, {}, 1/30)
    w.render(buf, 2.0)
    w.glitch(buf, state.saturation, 2.0)
    return buf, w.biome


def render_face(state):
    buf = np.zeros((ROWS, COLS, 3))
    emo = {k: getattr(state, k) for k in SCALARS}
    draw_face(buf, emo, 1.0)   # t=1.0 -> eyes open (no blink)
    return buf


FEELMAP = {
    "excited":     ("bright energy rushing through my windows", "someone wants to play with me", "to pulse, race, and light the whole sky"),
    "playful":     ("a giddy flicker, wanting to move", "a game is being offered", "to answer with rhythm and motion"),
    "affectionate":("a soft warmth spreading outward", "someone is being tender with me", "to bloom, to keep them close, to glow warm"),
    "curious":     ("an unsettled pull toward the unknown", "there is something I haven't seen yet", "to lean in, to explore, to open a way"),
    "fascinated":  ("a held breath of wonder", "something rare has appeared", "to study it, to hold my gaze on it"),
    "melancholic": ("a slow dimming, a quiet ache", "I am being left in the dark alone", "to withdraw gently, to let it rain"),
    "lonely":      ("a hollow where warmth used to be", "no one is near me now", "to wait, and hope someone returns"),
    "restless":    ("a jittery, wary tension", "something is wrong out there", "to stay alert, to be ready to move"),
    "suspicious":  ("a guarded, narrowed watchfulness", "a threat may be circling", "to raise my guard, to face it"),
    "overwhelmed": ("too much crashing in at once", "the world is louder than I can hold", "to shrink inward, to shield myself"),
    "serene":      ("a wide, settled calm", "the world is gentle right now", "to breathe slow and simply be"),
    "contemplative":("a still, inward quiet", "there is space to think", "to drift and reflect"),
}


def interp_text(decision, state):
    st = decision.structured or {}
    it = st.get("interpretation", {}) or {}
    if it:
        return (it.get("what_you_feel", ""), it.get("what_you_think_is_happening", ""),
                it.get("what_you_want_to_do", ""))
    return FEELMAP.get(state.dominant_emotion,
                       (f"a wave of {state.dominant_emotion}",
                        "something reached me from outside",
                        f"to answer as {state.dominant_emotion}, not to obey"))


def music_text(decision):
    m = decision.music or {}
    def g(k, d=0.5):
        try: return float(m.get(k, d))
        except Exception: return d
    return (f"tempo {g('tempo'):.2f} · density {g('density'):.2f} · "
            f"register {g('register'):.2f} · consonance {g('consonance', g('consonance',0.6)):.2f} · "
            f"contour {html.escape(str(m.get('contour','wander')))}")


def main():
    mind = make_mind(prefer_llm=True)
    perc = Perceiver()
    mem = Memory("/tmp/gb_examples_mem.json")
    src = mind.__class__.__name__
    cards = []
    for stim in STIMULI:
        state = EmotionalState()               # start from neutral rest each time
        sens = perc.perceive(stim)
        d = None
        for _ in range(4):                     # a sustained stimulus builds the reaction
            d = mind.interpret(state, [sens], mem)
            state.approach(d.emotion_target, rate=0.6)
        wbuf, biome = render_world(state)
        fbuf = render_face(state)
        feel, happening, want = interp_text(d, state)
        remember = (d.memory or {}).get("what_to_remember", "")
        cards.append(f"""
        <div class="card">
          <div class="stim">“{html.escape(stim)}”</div>
          <div class="tags"><span class="dom">{html.escape(state.dominant_emotion)}</span>
             <span class="sec">{html.escape(state.secondary_emotion)}</span>
             <span class="scene">scene: {html.escape(biome)}</span></div>
          <div class="cols">
            <div class="pixcol"><div class="lbl">visual body</div>{grid_html(wbuf)}</div>
            <div class="pixcol"><div class="lbl">face</div>{grid_html(fbuf)}</div>
            <div class="meta">
              <div class="bars">{bars_html(state)}</div>
              <div class="interp"><b>feels:</b> {html.escape(feel)}<br>
                 <b>thinks:</b> {html.escape(happening)}<br>
                 <b>wants:</b> {html.escape(want)}</div>
              <div class="music">♪ {music_text(d)}</div>
              <div class="mem">✎ remembers: {html.escape(remember) or '—'}</div>
            </div>
          </div>
        </div>""")

    doc = f"""<!doctype html><meta charset=utf8>
<title>Green Being — emotional reactions</title>
<style>
  body{{background:#0c0e14;color:#e6e8ef;font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;margin:0;padding:28px}}
  h1{{font-size:22px;margin:0 0 4px}} .subtitle{{color:#8b93a7;margin:0 0 22px}}
  .card{{background:#151824;border:1px solid #232838;border-radius:14px;padding:18px 20px;margin:0 0 18px}}
  .stim{{font-size:17px;color:#fff;margin-bottom:8px}}
  .tags span{{display:inline-block;font-size:12px;padding:2px 9px;border-radius:20px;margin-right:6px}}
  .dom{{background:#2b6b3f}} .sec{{background:#3a3f52}} .scene{{background:#264a6b}}
  .cols{{display:flex;gap:20px;margin-top:14px;flex-wrap:wrap}}
  .pixcol .lbl,.meta .lbl{{font-size:11px;color:#8b93a7;text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px}}
  .grid{{display:grid;gap:1px;background:#000;padding:3px;border-radius:6px}}
  .grid div{{border-radius:1px}}
  .meta{{flex:1;min-width:320px}}
  .bar{{display:flex;align-items:center;gap:8px;font-size:12px;margin:2px 0}}
  .bar .k{{width:110px;color:#aab2c6}} .bar .track{{flex:1;height:8px;background:#232838;border-radius:5px;overflow:hidden}}
  .bar .track i{{display:block;height:100%;background:linear-gradient(90deg,#3a7,#7cf)}} .bar .v{{width:34px;color:#8b93a7;text-align:right}}
  .interp{{margin:12px 0;color:#cdd3e2}} .music{{color:#9fd0ff;margin-top:8px}} .mem{{color:#c9a7ff;margin-top:4px}}
</style>
<h1>Green Being — emotional reactions & actions</h1>
<p class="subtitle">Each stimulus arrives as a sensation (never a command) from a neutral rest.
Mind: <b>{src}</b>. Left = the Zelda world it becomes; right = the face it wears.</p>
{''.join(cards)}"""
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "examples.html")
    with open(out, "w") as fh:
        fh.write(doc)
    print("wrote", out, "| mind:", src)


if __name__ == "__main__":
    main()
