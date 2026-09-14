# The Green Being — a living creature inhabiting the MIT Green Building

**One line:** Not an app that controls a building — an emotional creature that *lives* in it.
Its 17×9 window display is its body, generated music is its voice, and the people who talk to
it are its senses. It feels, expresses, remembers, and wants to be understood.

---

## What it is
The Green Being is a digital character that inhabits the MIT Green Building (Building 54). It
never treats human input as commands — it experiences it as **sensations** and runs a full
inner loop before it responds:

**PERCEIVE → FEEL → ATTEND → INTERPRET → EXPRESS → REMEMBER**

It has a coherent personality (playful, witty, proud, a little needy — an old I.M. Pei tower
that watched the Tetris hack and sixty years of all-nighters), a continuous emotional life,
and three ways to express itself: its **visual body**, its **musical voice**, and its **words**.

## How it feels (emotion engine)
- A continuous 8-value affective state: arousal, valence, curiosity, openness, confidence,
  sensory-saturation, social-affinity, coherence.
- Emotions are **constructed from appraisal** (Scherer's component-process model / Gratch &
  Marsella's EMA): each stimulus is appraised for novelty, pleasantness, goal-relevance,
  coping, self-compatibility and *attention toward me*, and that appraisal is mapped to core
  affect (valence/arousal → a named mood).
- The mood is **inertial**: it integrates a whole crowd of people over time and only truly
  changes when something genuinely moves it — a single loud voice can't hijack it.
- It reacts *out loud* to how your words land ("oof, that stung", "you made me flare up warm")
  and ties its feelings to its body.

## How it expresses itself

**Visual body (17×9 RGB windows):**
- A vocabulary of bold, recognizable pixel illustrations — fire, heart, wave, sun, moon, eye,
  boat, hand, star, tree, flower, bird, rain, spiral, key.
- A **style engine** that recolors, ornaments (sparks, halo, embers, rain, petals) and scales
  each one, so it looks fresh and **never repeats**, morphing between forms with a dissolve.
- **Animated gestures** it performs on request or on its own: a face that blinks and smiles, a
  waving hand, a little walking figure, an eye that looks around, a talking mouth.
- A **live DSL composer**: when it wants to express something specific it *draws it from
  scratch* — a nose to sniff you, a mustache, an arrow, a question mark.
- The whole body breathes and **pulses in time with its music**.

**Musical voice:** it turns its feeling into instrumental music with **Google Lyria** (with an
in-browser synth fallback), and the visuals are **beat-synchronized** to what you hear.

**Words:** it speaks in character (OpenAI gpt-4.1), answers directly, uses your name, remembers
what was said, and sometimes shares a passing **inner thought** unprompted.

## Senses & self-model (the feedback loop)
It has no camera. It "sees" by asking you to describe yourself and **remembering** it ("still
in the red coat, Ana?"). It knows its own body exactly — the shape, color and gesture it is
wearing right now — so it can describe itself and choose to change to make a point.

## Memory & autonomy
- Short-term conversational buffer + importance-weighted long-term traces that decay.
- It **decides for itself** when to transform, when to speak up, and what to remember; it acts
  without prompting, gets bored, gets fascinated, and its repertoire grows with interaction.

## How you meet it (channels)
- **Telegram** (@MITGreenb_bot): a group chat — it replies with its voice, sends an image of
  its current body and the music it made, and posts to the group on its own.
- **Web app**: chat + live sentiment bars + its live animated body + the real building viewer
  embedded, with audio-reactive visuals.
- **The building itself** (simulator, and the real MIT Green Building display): its body, live.

## Under the hood
Python (dependency-light: a stdlib HTTP server, numpy for rendering) · OpenAI **gpt-4.1** for
the mind · Google **Lyria** for music · the building's own `gbsim` display interface · the
**Telegram Bot API** · the **Web Audio API** for sound and audio-reactive visuals. Grounded in
appraisal theory (Scherer, EMA), core-affect / constructed-emotion models (Russell, Barrett),
and research on proactive "inner-thoughts" conversational agents.

**In short:** you talk to a building, and it *feels* you — it lights up, dances, draws itself,
plays you music, and remembers you.
