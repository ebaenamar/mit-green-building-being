# The Green Being 🟩

A digital **creature that inhabits the MIT Green Building**. Its 17×9 window display is its
body, generated music is its voice, and the people who talk to it are its senses. It never
treats input as commands — it *feels* it, and expresses itself back.

**PERCEIVE → FEEL → ATTEND → INTERPRET → EXPRESS → REMEMBER**

You talk to it (Telegram or a web app) and it lights up, changes shape, plays you music,
draws things, and remembers you — with a continuous, inertial emotional life and an
unmistakably MIT personality (Building 54: I.M. Pei, the radar dome, the Tetris hack).

See **[FICHA.md](FICHA.md)** for the full description.

---

## Features
- **Appraisal-based emotion engine** (Scherer / EMA → core affect): a continuous 8-value mood
  with inertia that integrates a whole crowd and only shifts when genuinely moved.
- **Visual body (17×9):** a vocabulary of recognizable emblems (fire, heart, wave, sun, moon,
  eye, boat, hand, star, tree, flower, bird, rain, spiral, key) with a style engine
  (recolor / ornament / scale) so it never repeats, plus morphing transitions and a beat that
  pulses with the music.
- **Animated gestures on request:** a face that blinks & smiles, a waving hand, a walking
  figure, an eye, a mouth — shown instantly.
- **Live pixel-art composer:** paints *any* object from scratch (a beach, a nose, a mustache,
  a piano…) directly onto the grid.
- **Musical voice:** turns feeling into instrumental music with **Google Lyria**, with an
  in-browser synth fallback and audio-reactive visuals.
- **Words:** speaks in character (OpenAI **gpt-4.1**), reacts to how your words land, and
  shares unprompted inner thoughts.
- **Channels:** a **Telegram** bot, a **web app** (chat + live sentiment + live animated body
  + embedded building viewer), and the building display itself.
- **Memory & autonomy:** short-term conversation buffer + decaying long-term traces; it decides
  when to transform, when to speak, and what to remember.

## Layout
```
being/            the creature
  mind.py         persona + appraisal-based emotion (OpenAI) + reflex fallback
  state.py        the continuous, inertial emotional state
  perception.py   raw input -> a sensation
  emblem_registry.py / styled.py   recognizable emblems + style engine
  gestures.py     animated body parts (face, hand, walk, eye, nose, mouth)
  glyph.py        primitive + pixel-art renderers (draw anything)
  morph.py        transformation between forms
  music.py / lyria.py   musical voice (synth + Google Lyria)
  telegram.py / pngutil.py   Telegram channel + PNG of the body
  being.py        the orchestrator (body loop, mind loop, muse loop, refresh loop)
webapp/           server.py + index.html (chat, live body, audio-reactive visuals)
run.py            local terminal preview / selftest
```

## Run it
Requires Python 3.10+ and `numpy`. The building interface (`gbsim`) is vendored.

```bash
pip install -r requirements.txt

# Web app + Telegram bot + drive a Green Building sim instance:
export OPENAI_API_KEY=sk-...        # the mind (gpt-4.1); without it, a reflex mind runs
export GEMINI_KEY=AIza...           # Google Lyria music (optional; synth fallback otherwise)
export TELEGRAM_TOKEN=123:ABC...    # a Telegram bot from @BotFather (optional)
export GB_INSTANCE=<your-instance>  # an instance from the Green Building simulator
python3 webapp/server.py           # -> http://localhost:8010

# Or just watch it locally, no keys needed:
python3 run.py            # terminal preview
python3 run.py --selftest # render a scripted mood journey
```

Tuning knobs (env): `OPENAI_MODEL`, `GB_REACT_RATE` (emotional stubbornness),
`GB_INVITE_COOLDOWN`, `GB_AUTONOMY`.

## Credits
Built on the MIT Green Building display interface and simulator
([`gbsim` / sundai-greenbuilding-sim](https://github.com/willsarg/sundai-greenbuilding-sim),
display by Nevin Thinagar and the 2026 hackers). Mind: OpenAI. Music: Google Lyria.
