#!/usr/bin/env python3
"""Drive the being on a simulator instance and walk it through an emotional journey
so the Zelda world visibly shifts. Watch it at the instance's view_url.

  python3 demo_live.py calm-toad http://localhost:8787/api

Uses the reflex mind by default (instant, no API cost). Pass --llm to use OpenAI.
"""
import sys
import threading
import time

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))

from gbsim import WebDisplay
from being.being import Being
from being.mind import make_mind

JOURNEY = [
    (3, None),                                   # wake: calm overworld
    (0, "hello there, beautiful building"),      # gentle greeting -> warmer
    (4, "i love watching you glow at night"),    # affection -> meadow, hearts
    (5, "let's play! run run run!!!"),           # energetic -> curiosity/arousal
    (4, "what's inside that cave? i wonder..."), # curious -> cave, rupees
    (5, "DANGER! something is chasing us!!!"),   # fear+arousal -> action, octoroks
    (5, "i feel so alone in the cold dark"),     # melancholy -> night forest, rain
    (5, "so many voices all at once so loud!!!"),# overload -> dungeon, glitch
    (6, "shhh... rest now, quiet and still"),    # calm returns
]


def main():
    if len(sys.argv) < 2:
        print("usage: python3 demo_live.py <instance> [base_url] [--llm]")
        sys.exit(1)
    name = sys.argv[1]
    base = "http://localhost:8787/api"
    use_llm = "--llm" in sys.argv
    for a in sys.argv[2:]:
        if a.startswith("http"):
            base = a

    display = WebDisplay(name, base_url=base)
    being = Being(display, mind=make_mind(prefer_llm=use_llm), voice=None,
                  state_path="", memory_path="/tmp/gb_demo_mem.json",
                  autonomy_period=6.0)

    def journey():
        time.sleep(1.0)
        while not being._stop.is_set():
            for wait, line in JOURNEY:
                if being._stop.is_set():
                    break
                if line:
                    print(f"  » stimulus: {line}")
                    being.feel(line)
                time.sleep(wait)
            print("  (journey loops...)")

    threading.Thread(target=journey, daemon=True).start()
    print(f"Being alive on '{name}'. Watch: {base.rsplit('/api',1)[0]}/{name}")
    try:
        being.run()
    except KeyboardInterrupt:
        being.stop()


if __name__ == "__main__":
    main()
