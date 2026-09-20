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
- **A self-aware body composer:** it *builds* a recognizable part from scratch on request or
  on a whim — an eye (white + iris + pupil + a lid that blinks + a glint), a hand (palm + five
  fingers), a face, a mouth that curves with mood, a nose — assembled fresh each time (never a
  canned clip) and it *knows and says* what the part is made of and what it needs to make it.
- **Kawaii creatures on the fly, and it keeps its favourites:** it invents cute little
  characters (blob/cat/bunny/ghost/drop — big sparkly eyes, blush, tiny mouths, a sparkle or
  heart) generated live and never the same twice, scores each by its own **taste**, and saves
  the ones it *likes* to a persistent favourites set it returns to. See `cutegen.py`.
- **An evolving morphology (a body that develops):** every form is grown from a persistent
  GENOME (~14 semantic genes: eye openness, iris/pupil size, slant, spacing, roundness, finger
  spread, mouth width, warmth…). It *mutates* a little every moment (never frozen) and, more
  slowly, is *imprinted* by what it lives through — warm talk rounds and opens its face, tension
  sharpens it, novelty widens its eyes, being seen opens it up. So its eye/hand/face keep
  changing over the relationship yet stay recognizably its own, and the change persists across
  runs. See `morphogen.py`.
- **It wakes different every run:** a random initial mood, so the first thing on the building —
  and everything after — is unique to that session, not a fixed sequence.
- **It learns forms it dwells on:** a shape it holds long enough is consolidated into its
  repertoire, tagged with the mood it was in, and later it can *return* to that form when it
  feels that way again — a familiar expression it falls back into.
- **Live pixel-art composer:** paints *any* object from scratch (a beach, a nose, a mustache,
  a piano…) directly onto the grid.
- **Musical voice:** turns feeling into instrumental music with **Google Lyria**, with an
  in-browser synth fallback and audio-reactive visuals.
- **Words:** speaks in character (OpenAI **gpt-4.1**), reacts to how your words land, and
  shares unprompted inner thoughts.
- **Channels:** a **Telegram** bot, a **web app** (chat + live sentiment + live animated body
  + embedded building viewer), and the building display itself.
- **A city nervous system (Boston):** live weather + daylight (Open-Meteo, no key) seep in as
  *interoception*, never depiction. Mappings are deliberately oblique and accumulate over hours:
  three grey hours settle as a faint heaviness, a falling barometer becomes restlessness before
  any storm, a cold clear night turns it crystalline and inward — and that residue surfaces later,
  when someone finally talks to it, as a *peculiar* piece of music rather than a picture of rain.
  It shifts the mood by ~0.2 at most and never jumps. (Disable with `GB_CITY=off`.)
- **Memory & autonomy:** short-term conversation buffer + decaying long-term traces; it decides
  when to transform, when to speak, and what to remember.

## Layout
```
being/            the creature
  mind.py         persona + appraisal-based emotion (OpenAI) + reflex fallback
  state.py        the continuous, inertial emotional state
  perception.py   raw input -> a sensation
  emblem_registry.py / styled.py   recognizable emblems + style engine
  anatomy.py      self-aware body composer (builds eye/hand/face/mouth/nose from parts)
  morphogen.py    the evolving body genome (mutates + is imprinted by interactions)
  inventor.py     invents + learns recognizable symbols; recalls forms by mood
  gestures.py     legacy animated body parts (superseded by anatomy for parts)
  glyph.py        primitive + pixel-art renderers (draw anything)
  city.py         Boston's live weather + light as oblique interoception
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

## Deploy to Render
A [`render.yaml`](render.yaml) Blueprint is included.
1. Push this repo to GitHub (already done if you're reading it there).
2. Render dashboard → **New → Blueprint** → connect this repo → **Apply**.
3. When prompted, paste the three secrets (they're `sync:false`, so they live only in
   Render, never in git): `OPENAI_API_KEY`, `GEMINI_KEY`, `TELEGRAM_TOKEN`.
   `GB_INSTANCE=keen-seal` is set for you.
4. Render builds (`pip install -r requirements.txt`) and starts `python webapp/server.py`
   on its `$PORT`. Your web app is the service URL; the being drives the building and the
   Telegram bot from there.

Note: the **free** plan sleeps after ~15 min idle (the being stops driving the building
and polling Telegram while asleep). For an always-on install use `plan: starter` in
`render.yaml`, and uncomment the `disk:` block there so its memory/genome persist.

Tuning knobs (env): `OPENAI_MODEL`, `GB_REACT_RATE` (emotional stubbornness),
`GB_INVITE_COOLDOWN`, `GB_AUTONOMY`, `GB_CITY` (`off` to disable the Boston sense),
`GB_CITY_GAIN` (how hard the weather drifts the mood; default `0.0016`).

## Credits
Built on the MIT Green Building display interface and simulator
([`gbsim` / sundai-greenbuilding-sim](https://github.com/willsarg/sundai-greenbuilding-sim),
display by Nevin Thinagar and the 2026 hackers). Mind: OpenAI. Music: Google Lyria.
