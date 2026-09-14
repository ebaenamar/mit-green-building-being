#!/usr/bin/env python3
"""Bring the being to life.

  python3 run.py                       # local terminal viewer (no key, no instance needed)
  python3 run.py --instance adjective-animal   # drive the real Green Building sim
  python3 run.py --no-voice            # silent
  python3 run.py --selftest            # headless: render a scripted mood journey, print stills

Type sensations and press Enter; they arrive as feelings, not commands. Ctrl-C to leave.
Set OPENAI_API_KEY to give it the LLM mind; without it, the built-in reflex mind runs.
"""
from __future__ import annotations
import argparse
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from being.being import Being
from being.mind import make_mind
from being.voice import Voice
from being.local_display import LocalDisplay

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def _stdin_pump(being, stop):
    for line in sys.stdin:
        if stop.is_set():
            break
        being.feel(line)


def selftest():
    """Headless proof of life: run several moods and print a still of each."""
    import numpy as np
    from being.render import ZeldaWorld, ROWS, COLS
    from being.state import EmotionalState

    def show(buf, title):
        print(f"\n=== {title} ===")
        for r in range(ROWS):
            row = ""
            for c in range(COLS):
                v = buf[r, c]
                row += f"\x1b[48;2;{int(v[0]*255)};{int(v[1]*255)};{int(v[2]*255)}m  "
            print(row + "\x1b[0m")

    moods = {
        "serene overworld (calm, pleasant)":
            dict(arousal=.25, valence=.7, curiosity=.4, social_affinity=.4,
                 saturation=.0, coherence=.8, confidence=.6),
        "affectionate meadow (hearts)":
            dict(arousal=.4, valence=.8, curiosity=.4, social_affinity=.85,
                 saturation=.0, coherence=.8, confidence=.6),
        "curious cave (seeking, rupees)":
            dict(arousal=.55, valence=.55, curiosity=.85, social_affinity=.4,
                 saturation=.1, coherence=.6, confidence=.6),
        "roused action (octoroks, sword)":
            dict(arousal=.85, valence=.35, curiosity=.5, social_affinity=.3,
                 saturation=.2, coherence=.5, confidence=.7),
        "melancholic night forest (rain)":
            dict(arousal=.25, valence=.25, curiosity=.3, social_affinity=.2,
                 saturation=.1, coherence=.6, confidence=.4),
        "overloaded dungeon (glitch)":
            dict(arousal=.7, valence=.35, curiosity=.4, social_affinity=.3,
                 saturation=.85, coherence=.3, confidence=.4),
    }
    for title, vals in moods.items():
        s = EmotionalState(**vals)
        w = ZeldaWorld(time_of_day=0.5 if "night" not in title else 0.95)
        buf = np.zeros((ROWS, COLS, 3))
        for i in range(90):            # ~3 s so the world scrolls into a good frame
            w.update(s, {}, 1 / 30)
        w.render(buf, 3.0)
        w.glitch(buf, s.saturation, 3.0)
        show(buf, title)
    print("\nselftest ok — all six moods rendered.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--instance", help="Green Building sim instance name (adjective-animal)")
    ap.add_argument("--base-url", default="https://sundai.willsarg.com/api")
    ap.add_argument("--no-voice", action="store_true")
    ap.add_argument("--no-llm", action="store_true")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--time", type=float, default=0.5, help="time of day 0..1 (0/1=night)")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        selftest()
        return

    if args.instance:
        from gbsim import WebDisplay
        display = LocalDisplay(status_fn=None)  # placeholder; replaced below
        display = WebDisplay(args.instance, base_url=args.base_url)
        local = None
    else:
        display = None  # set after being exists so status_fn can read it

    mind = make_mind(prefer_llm=not args.no_llm)
    voice = None if args.no_voice else Voice()

    if args.instance:
        being = Being(display, mind=mind, voice=voice,
                      state_path=os.path.join(DATA, "state.json"),
                      memory_path=os.path.join(DATA, "memory.json"),
                      fps=args.fps, time_of_day=args.time)
    else:
        holder = {}
        ld = LocalDisplay(status_fn=lambda: holder["b"].status())
        being = Being(ld, mind=mind, voice=voice,
                      state_path=os.path.join(DATA, "state.json"),
                      memory_path=os.path.join(DATA, "memory.json"),
                      fps=args.fps, time_of_day=args.time)
        holder["b"] = being

    stop = threading.Event()
    threading.Thread(target=_stdin_pump, args=(being, stop), daemon=True).start()
    src = "OpenAI" if mind.__class__.__name__ == "LlmMind" else "reflex (no OPENAI_API_KEY)"
    if args.instance:
        print(f"Being awake on '{args.instance}'. Mind: {src}. "
              f"View: {args.base_url.rsplit('/api',1)[0]}/{args.instance}")
        print("Type sensations + Enter. Ctrl-C to leave.")
    try:
        being.run()
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        being.stop()
        time.sleep(0.2)
        try:
            display and display.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
