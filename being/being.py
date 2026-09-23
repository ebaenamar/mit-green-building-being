"""The orchestrator: one continuous creature running two coupled loops.

  BODY loop  (~30 fps): always alive. Eases the emotional state toward the mind's
             latest target, drives the Zelda world from that feeling, renders and
             sends frames. Fires an instant spark the moment a stimulus lands.
  MIND loop  (on stimulus, and periodically for autonomy): runs PERCEIVE/FEEL/
             ATTEND/INTERPRET, produces a Decision, speaks, and REMEMBERs.

Inputs are pushed in as sensations; they are never commands.
"""
from __future__ import annotations
import math
import os
import threading
import time

import numpy as np

from gbsim.display import Color
from .render import ZeldaWorld, ROWS, COLS
from .perception import Perceiver
from .memory import Memory
from .state import EmotionalState
from .mind import make_mind, _label, appraisal_to_target
from .morph import Expression
from .inventor import Library, invent
from .morphogen import Genome
from .drives import Drives
from . import emblem_registry, styled, gestures, anatomy, facade, cutegen
from .glyph import render_glyph, render_pixels


# A rotating repertoire of response SHAPES, so it doesn't fall into one formula (the
# "witty confession + bounce it back with a dare" trap). One is drawn per reply and fed to
# the mind as a hard constraint; the same shape never fires twice in a row.
RESPONSE_MODES = [
    ("terse", "Answer in ONE short blunt line. Do NOT ask anything back."),
    ("plain", "Just answer plainly and stop — no question back, no challenge, no flourish."),
    ("tangent", "Don't answer directly; drift into a small specific tangent or an old memory."),
    ("joke", "Be light — a quick joke, a tease, or something silly. Keep it short."),
    ("brag", "Brag about something specific, then drop it. No question back."),
    ("feeling", "React with just a feeling, a few words, almost under your breath."),
    ("ask", "Ask THEM one short, specific, genuinely curious thing."),
    ("deflect", "Be a little evasive — dodge, change the subject to something you noticed."),
    ("agree", "Simply agree or riff along, briefly, without turning it into a contest."),
    ("blunt_confession", "Confess something plainly, then let it sit. Do NOT dare them back."),
]


# the LLM's per-turn face emotion -> (valence, arousal) target + a facade gesture, so the
# SCREEN visibly tracks the conversation as it happens.
EXPRESSIONS = {
    "happy": (0.85, 0.60, "bloom"), "love": (0.90, 0.55, "bloom"),
    "playful": (0.78, 0.62, "bloom"), "curious": (0.62, 0.60, "perk"),
    "surprised": (0.60, 0.90, "perk"), "sad": (0.28, 0.30, "withdraw"),
    "angry": (0.30, 0.80, "ripple"), "suspicious": (0.40, 0.58, None),
    "sleepy": (0.50, 0.22, None), "neutral": None,
}
# expression -> the crisp face emotion to SHOW when reacting to a message
FACE_MODE = {
    "happy": "happy", "love": "happy", "playful": "happy", "curious": "surprised",
    "surprised": "surprised", "sad": "sad", "angry": "angry", "suspicious": "angry",
    "sleepy": "sleepy", "neutral": "neutral",
}


class Being:
    def __init__(self, display, mind=None, voice=None, state_path="", memory_path="",
                 fps=30, autonomy_period=7.0, time_of_day=0.5, express_mode="glyph",
                 library_path="", view_url="", on_event=None, city=None, genome_path="",
                 transit=None):
        self.view_url = view_url
        self.on_event = on_event      # called with a dict when the being speaks to the group
        self.display = display
        self.mind = mind or make_mind()
        self.voice = voice
        self.city = city              # Boston's live weather/light as interoception (optional)
        self.transit = transit        # the T (Red Line at Kendall/MIT) under it (optional)
        self.fps = fps
        self.autonomy_period = autonomy_period
        self.express_mode = express_mode      # "glyph" (emblems), "world" (Zelda), "face"

        # Persisted continuity when a state file exists; otherwise wake in a fresh, random
        # mood so the being genuinely starts each run feeling — and expressing — something new.
        self.state = EmotionalState.load(state_path) if state_path else EmotionalState.random()
        self.memory = Memory(memory_path) if memory_path else Memory("/tmp/gb_mem.json")
        self.state_path = state_path
        self.perceiver = Perceiver()
        self.world = ZeldaWorld(time_of_day=time_of_day)
        self.expr = Expression()              # glyph metamorphosis engine
        self.library = Library(library_path)  # invented emblems, grows with interaction
        self.morph = Genome(genome_path)      # the being's evolving body morphology
        self.drives = Drives()                # needs that push it to act on its own
        self._spark = 0.0
        self._glyph_name = ""
        self._style_i = 0
        self._last_expr_dom = ""
        # inertia: how strongly each message / drift moves the persistent mood. Small, so
        # one loud person can't hijack it — the crowd is integrated over time.
        self._react_rate = float(os.environ.get("GB_REACT_RATE", "0.30"))
        self._drift_rate = 0.06
        self._convo = []              # short conversational buffer (who: text / me: ...)
        self._last_invite = 0.0       # so it doesn't keep begging "look at my body"
        self._invite_cd = float(os.environ.get("GB_INVITE_COOLDOWN", "200"))
        self._impact = 0.5            # how well its expressions are landing (0..1, EMA)
        self._body_since = time.time()
        self._last_style = {}         # style of the emblem it is currently wearing
        self._hold_until = 0.0        # keep a requested gesture/drawing on screen this long
        self._making = None           # manifest of a body part it is deliberately building
        self._mode_hint = ""          # the required response shape for the current reply
        self._len_hint = ""           # the required response length for the current reply
        self._returned = False        # someone just came back after a silence (perk up)
        self._will_show = ""          # the form we're about to put on the windows this turn
        self.viewers = 0              # how many are watching the building live right now
        self._last_lines = []         # its own recent utterances (to avoid repeating the shape)
        self._last_music = 0.0        # last time it offered music (rationed)
        self._music_cd = float(os.environ.get("GB_MUSIC_COOLDOWN", "150"))
        self._last_mode = ""          # last response-shape so it doesn't repeat
        self._cur_spec = None         # the DSL spec of the form on screen (if composable)
        self._cur_form_name = ""      # its name
        self._cur_learnable = False   # eligible to be consolidated if held long enough
        self._learn_hold = float(os.environ.get("GB_LEARN_HOLD", "12"))
        self._scalars = ("arousal", "valence", "curiosity", "openness", "confidence",
                         "saturation", "social_affinity", "coherence")
        self.buf = np.zeros((ROWS, COLS, 3), dtype=float)
        self._fg = np.zeros((ROWS, COLS, 3), dtype=float)    # the face/emblem layer
        self._wash = np.zeros((ROWS, COLS, 3), dtype=float)  # the whole-facade mood field
        self._facade_event = None                            # transient legible facade gesture
        self._last_rumble = 0.0                               # last time the T rumbled through
        self._lock = threading.Lock()
        self._pending = []                 # raw stimuli awaiting the mind
        self._target = None                # emotional target the body eases toward
        self._hint = {}
        self._approach = 1.6
        self._stop = threading.Event()
        self._mind_src = self.mind.__class__.__name__
        self._last_line = ""
        if self.express_mode == "glyph":          # something to show before the first thought
            self._relabel()                        # name the random waking mood first
            # invent the first body FROM that mood, so the very first thing on the building
            # is unique to this run — recognizable, but never the same shape twice.
            try:
                nm, spec = invent(self.state)
                self.library.remember(nm, spec)
                self.expr.set_render((lambda buf, t, g=spec: render_glyph(buf, g, t)), nm + "#0")
                self._cur_spec, self._cur_form_name, self._cur_learnable = spec, nm, True
            except Exception:
                nm, _ = emblem_registry.pick(self.state)
                self.expr.set_render(styled.make_styled(nm, styled.style_for(self.state, 0)), nm + "#0")
            self._glyph_name = nm
            self._last_expr_dom = self.state.dominant_emotion

    def _showing(self) -> str:
        """One CLEAN description of what's on the windows this turn — never an internal code
        like 'playful-starxkey-0f8'. Prefers what we're about to show this reply."""
        import re
        raw = (self._will_show or self._glyph_name or "your lit windows").strip()
        # invented-glyph codes ('playful-star-c57', 'playful-starxkey-0f8') -> generic + honest
        if " " not in raw and re.search(r"-\w{2,4}$", raw):
            return "a shape of light"
        return raw

    def _context(self) -> dict:
        """What the being knows about its own body + how it's landing — fed to the mind so
        it can talk about how it looks, choose what to express, and read its impact."""
        imp = ("really landing" if self._impact > 0.62 else
               "barely landing / they seem distant" if self._impact < 0.42 else "landing okay")
        ctx = {"body": f"{self._showing()} on your 153 windows right now", "impact": imp}
        if self._mode_hint:
            ctx["style"] = self._mode_hint
        if self._len_hint:
            ctx["length"] = self._len_hint
        if self._last_lines:
            ctx["avoid"] = " | ".join(self._last_lines[-3:])
        try:
            dl = self.drives.context_line()
            if dl:
                ctx["needs"] = dl
        except Exception:
            pass
        if self._returned:
            ctx["presence"] = ("Someone just came BACK after a long silence — you noticed, "
                               "and it moved you. Let that land (relief, or a bit of 'oh, finally').")
        showing = self._showing()
        watchers = ""
        if self.viewers > 0:
            watchers = (" Lots of people are" if self.viewers >= 5 else f" {self.viewers} " +
                        ("person is" if self.viewers == 1 else "people are")) + \
                       " standing in Cambridge looking at your windows live right now."
        ctx["watched"] = (f"Your 153 windows are showing {showing} this turn.{watchers} DON'T narrate "
                          f"your display every reply — mostly just talk. But IF you mention what "
                          f"you're showing, it MUST be exactly '{showing}' — never invent a different "
                          f"shape and never say an internal code.")
        if self._making:
            ctx["making"] = (f"You are BUILDING a {self._making['name']} on your body right now, "
                             f"from scratch. It's made of {self._making['needs']}. Say what you're "
                             f"assembling as you show it — you KNOW exactly what it needs.")
        if self.city:
            try:
                ctx["weather"] = self.city.context_line()
            except Exception:
                pass
        if self.transit:
            try:
                ctx["transit"] = self.transit.context_line()
            except Exception:
                pass
        return ctx

    def _lyria_prompt(self) -> str:
        """The Lyria text prompt for how it feels, tinted obliquely by the city's residue
        (an afternoon of rain surfacing later as something peculiar)."""
        from .music import lyria_prompt
        p = lyria_prompt(self.state)
        if self.city:
            try:
                p = self.city.color_prompt(p)
            except Exception:
                pass
        return p

    # -- outside world pokes the being -------------------------------------
    def feel(self, raw: str):
        """A sensation arrives. Acknowledge instantly; interpret later."""
        raw = (raw or "").strip()
        if not raw:
            return
        with self._lock:
            self._pending.append(raw)
            self._last_line = raw
        self._spark = 1.0                  # reflex: "I noticed you", before any thinking
        self.world.flash()
        self.world.look(4.0)               # (world/face modes)

    def react(self, text: str, speaker: str = "") -> dict:
        """Synchronously perceive -> interpret -> express, and return a rich reaction
        for a web client: sentiment, the being's voice, and music (synth + Lyria)."""
        from .music import phrase, lyria_direction, lyria_prompt
        text = (text or "").strip()
        sens = self.perceiver.perceive(text)
        with self._lock:
            self._last_line = text
            self._convo.append(f"{speaker or 'someone'}: {text}")
            self._convo = self._convo[-12:]
            convo = list(self._convo)
        self._spark = 1.0
        self.world.flash(); self.world.look(4.0)
        # presence: if it's been alone a while, it perks up harder when someone returns
        self._returned = self.drives.alone_seconds() > 90
        if self._returned:
            self._spark = 1.3
            self._fire_facade("perk", 1.6)          # the whole facade brightens: it noticed you

        # If they asked to SEE a body part, BUILD it from scratch on the screen INSTANTLY —
        # before the language model even answers. It knows what the part is made of and
        # assembles it fresh (a new eye/hand each time), not a canned animation.
        built = None
        pname = anatomy.detect(text) if self.express_mode == "glyph" else None
        if pname:
            fn, manifest, spec = anatomy.render_for(pname, self.state,
                                                    self.morph.express(pname, self.state))
            if fn:
                built = manifest
                self._making = manifest
                self._style_i += 1
                with self._lock:
                    self._glyph_name = pname
                    self._body_since = time.time()
                    self._last_style = {}
                self.expr.set_render(fn, f"anatomy:{pname}#{self._style_i}", dur=0.6)
                self._cur_spec, self._cur_form_name, self._cur_learnable = spec, pname, bool(spec)
                self._hold_until = time.time() + 14   # hold it so they see it (and it can be learned)

        # Decide WHAT the windows will show this turn BEFORE speaking, so the words can match the
        # image. Priority: a body part they asked for > an object they asked to see > an empathic
        # face reading how their message feels.
        req_emblem = self._requested_emblem(text) if (self.express_mode == "glyph" and not built) else ""
        felt = None
        if not built and not req_emblem:
            vt, en = sens.valence_tone, sens.energy_tone
            if vt < 0.45:
                felt = "sad" if en < 0.55 else "angry"
            elif vt > 0.60:
                felt = "happy"
            elif en > 0.80:
                felt = "surprised"
        if built:
            self._will_show = f"a {pname}"
        elif req_emblem:
            self._will_show = req_emblem
        elif felt:
            self._will_show = f"a {felt} face"      # empathic face we WILL render (matches)
        else:
            self._will_show = "your face"           # exact emotion decided later; stay generic

        self._mode_hint = self._pick_mode()        # force a fresh response shape this turn
        self._len_hint = self._pick_length()       # and a fresh length, so replies breathe
        decision = self.mind.interpret(self.state, [sens], self.memory,
                                       speaker=speaker, convo=convo, context=self._context())
        self._making = None
        self._mode_hint = self._len_hint = ""
        # when it just built a body part, make sure it SAYS what it assembled (the reflex
        # mind gets the construction line verbatim; the LLM already spoke about it via context)
        if built and (str(decision.source).startswith("reflex") or not decision.utterance):
            decision.utterance = anatomy.construction_line(built)
        # its expressions landing well/poorly is a feedback signal it can feel
        self._impact = 0.82 * self._impact + 0.18 * sens.valence_tone
        # every interaction leaves a tiny, lasting mark on its evolving body morphology
        try:
            self.morph.imprint(self.state, sens, self._impact)
        except Exception:
            pass
        # contact relieves loneliness/boredom (the drive context above already reached the mind)
        self.drives.on_interaction(novelty=sens.novelty, warmth=sens.valence_tone)
        # emotion is CONSTRUCTED from appraisal (Scherer/EMA) when available
        target = (appraisal_to_target(self.state, decision.appraisal)
                  if decision.appraisal else decision.emotion_target)
        with self._lock:
            self._mind_src = decision.source
            # gently nudge the persistent mood — one voice in a crowd, weighted by how
            # strong it is. The mood is inertial; it won't flip from a single message.
            if target:
                rate = min(0.6, self._react_rate * (0.6 + sens.intensity))
                self.state.approach(target, rate=rate, set_labels=False)
            # the face/facade track THIS message: the LLM's chosen expression nudges mood now
            em = EXPRESSIONS.get(decision.expression)
            if em:
                self.state.nudge(valence=(em[0] - self.state.valence) * 0.5,
                                 arousal=(em[1] - self.state.arousal) * 0.5)
            self._relabel()
        if em and em[2]:
            self._fire_facade(em[2], 2.0)
        # The body changes only if that nudge actually tipped the being into a new mood;
        # otherwise it just answers with words and keeps the body it already wears.
        # render EXACTLY what we told it it's showing (self._will_show), so words match image
        if built:
            body_changed = True                    # already showing the requested part; keep it
        elif self.express_mode == "glyph" and req_emblem:      # they asked to see this exact thing
            self._express_emblem(req_emblem, "")
            body_changed = False
        elif self.express_mode == "glyph" and decision.pixels:   # the AI painted a specific thing
            self._express_pixels(decision.pixels,
                                 name=(decision.body_intent[:24] or "a drawing"))
            body_changed = True
        elif self.express_mode == "glyph" and decision.glyph:   # the AI drew with primitives
            self._express_composed(decision.glyph,
                                   name=(decision.body_intent[:24] or decision.emblem or "a vision"),
                                   dur=decision.morph_secs)
            body_changed = True
        elif self.express_mode == "glyph" and emblem_registry.get(decision.emblem) and decision.emblem:
            self._express_emblem(decision.emblem, decision.body_intent)
            body_changed = False
        elif self.express_mode == "glyph":
            # DEFAULT: the empathic face reads how their message feels, held so it's a reaction.
            self._react_face(decision.expression, felt)
            body_changed = False
        else:
            body_changed = False
        self._will_show = ""                        # autonomy falls back to the real current form
        if decision.utterance:
            with self._lock:
                self._convo.append(f"me: {decision.utterance}")
                self._convo = self._convo[-12:]
                self._last_lines = (self._last_lines + [decision.utterance])[-3:]
        m = decision.memory or {}
        if m.get("what_to_remember"):
            self.memory.remember(m["what_to_remember"], m.get("importance", 0.4),
                                 mood=self.state.dominant_emotion, influence=m.get("influence", True))

        it = (decision.structured or {}).get("interpretation") or {}
        SCAL = self._scalars
        lp = self._lyria_prompt()
        if decision.music_wish:
            lp = decision.music_wish + " — " + lp
        import random
        music_req = any(w in text.lower() for w in (
            "music", "song", "sing", "play me", "play a", "tune", "beat", "melod",
            "canción", "cancion", "música", "musica", "suena", "tócame", "tocame", "toca "))
        # ration music: on explicit request always; otherwise only on a genuine shift, past a
        # cooldown, and not even every time — so it's an event, not a tic on every line.
        now = time.time()
        genuine_music = (body_changed and (now - self._last_music) > self._music_cd
                         and random.random() < 0.5)
        wants_music = bool(music_req or genuine_music)
        if wants_music:
            self._last_music = now
            self.drives.on_music()
        if body_changed:
            self.drives.on_transform()
        if not wants_music:                 # don't surface a music offer at all this turn
            lp = ""
        # human cadence, kept SNAPPY (many people waiting): quick when roused, a touch slower calm
        delay = 0.3 + 1.0 * (1 - self.state.arousal)
        return {
            "utterance": decision.utterance or "",
            "invite_to_look": self._gate_invite(decision.invite_to_look),
            "sentiment": {k: round(getattr(self.state, k), 3) for k in SCAL},
            "dominant": self.state.dominant_emotion, "secondary": self.state.secondary_emotion,
            "feels": it.get("what_you_feel", ""),
            "thinks": it.get("what_you_think_is_happening", ""),
            "wants": it.get("what_you_want_to_do", ""),
            "glyph": self._glyph_name,
            "body_changed": body_changed,
            "wants_music": wants_music,
            "music": phrase(decision.music),
            "lyria": lyria_direction(self.state),
            "lyria_prompt": lp,
            "music_wish": (decision.music_wish or "") if wants_music else "",
            "source": decision.source,
            "reply_delay": round(min(2.0, max(0.2, delay)), 2),
            "view_url": self.view_url,
        }

    def current_frame(self) -> dict:
        """The being's live body as pixels, so a web client can animate it like a GIF."""
        b = (np.clip(self.buf, 0.0, 1.0) * 255).astype(int)
        return {"w": COLS, "h": ROWS,
                "cells": [[int(b[r, c, 0]), int(b[r, c, 1]), int(b[r, c, 2])]
                          for r in range(ROWS) for c in range(COLS)]}

    def snapshot(self) -> dict:
        SCAL = ("arousal", "valence", "curiosity", "openness", "confidence",
                "saturation", "social_affinity", "coherence")
        return {"sentiment": {k: round(getattr(self.state, k), 3) for k in SCAL},
                "dominant": self.state.dominant_emotion, "glyph": self._glyph_name,
                "transforming": self.expr.transforming, "view_url": self.view_url,
                "bpm": int(60 + self.state.arousal * 120),
                "viewers": self.viewers,
                "repertoire": len(self.library),
                "favorites": len(self.library.favorites),
                "morphology": self.morph.summary(),
                "drives": self.drives.summary()}

    def status(self) -> str:
        if self.express_mode == "glyph":
            return (f"[{self._glyph_name or '...'}] {self.state.summary()} "
                    f"| mind:{self._mind_src} | repertoire:{len(self.library)} "
                    f"| last:{self._last_line[:20]}")
        return (f"[{self.world.biome}] {self.state.summary()} "
                f"| mind:{self._mind_src} | last:{self._last_line[:24]}")

    # -- run ----------------------------------------------------------------
    def run(self):
        if self.city:
            try:
                self.city.start()      # Boston starts seeping into the body
            except Exception as e:
                print(f"being: city sense failed to start: {e}")
        if self.transit:
            try:
                self.transit.start()   # the T starts rumbling under it
            except Exception as e:
                print(f"being: transit sense failed to start: {e}")
        mt = threading.Thread(target=self._mind_loop, name="being-mind", daemon=True)
        mt.start()
        threading.Thread(target=self._muse_loop, name="being-muse", daemon=True).start()
        threading.Thread(target=self._refresh_loop, name="being-refresh", daemon=True).start()
        threading.Thread(target=self._drives_loop, name="being-drives", daemon=True).start()
        self._body_loop()

    def _refresh_loop(self):
        """Keep the body looking alive and NEW: every so often the being re-expresses its
        current mood as a fresh variation (new colors, ornament, sometimes a sibling
        emblem) with a visible morph — without changing how it feels."""
        import random
        while not self._stop.is_set():
            for _ in range(int(random.uniform(22, 42))):   # calmer ambient pace, so reactions pop
                if self._stop.is_set():
                    return
                self._maybe_learn()                # consolidate a form it's been holding
                time.sleep(1)
            try:
                self.morph.save()                  # persist the evolving body periodically
            except Exception:
                pass
            if self.express_mode != "glyph" or self.expr.transforming:
                continue
            if time.time() < self._hold_until:     # a requested/held form is on screen
                continue
            self._style_i += 1
            roll = random.random()
            # ~20%: BUILD a big, recognizable body part from scratch (an eye that blinks &
            # looks around, a hand that waves, a face, a mouth, a nose) — assembled fresh, and
            # held long enough that it can be learned. This is the being showing you itself.
            if roll < 0.20:
                pname = random.choices(["face", "eye", "hand", "mouth", "nose"],
                                       weights=[6, 4, 4, 2, 2])[0]
                fn, _m, spec = anatomy.render_for(pname, self.state,
                                                  self.morph.express(pname, self.state))
                if fn:
                    with self._lock:
                        self._glyph_name = pname
                        self._last_style = {}
                        self._body_since = time.time()
                    self.expr.set_render(fn, f"anatomy:{pname}#{self._style_i}", dur=1.4)
                    self._cur_spec, self._cur_form_name, self._cur_learnable = spec, pname, bool(spec)
                    self._hold_until = time.time() + self._learn_hold + 1   # dwell so it's seen & learned
                    continue
            # ~30%: INVENT a cute little creature on the fly (kawaii: big eyes, blush, tiny
            # mouth, a sparkle) — and if it LIKES this one (its own taste), keep it forever.
            if roll < 0.50:
                spec = cutegen.generate(self.state, self.morph)
                sc = cutegen.score(spec, self.state, self.morph)
                liked = self.library.consider(spec, sc, self.state)
                with self._lock:
                    self._glyph_name = cutegen.describe(spec)
                    self._last_style = {}
                    self._body_since = time.time()
                    self._cur_spec, self._cur_learnable = None, False
                self.expr.set_render((lambda buf, t, s=spec: cutegen.render(buf, s, t)),
                                     f"cute:{spec['seed']}", dur=1.6)
                if liked:                            # a genuine little delight when it keeps one
                    self._fire_facade("bloom", 2.0)
                    if self.on_event and random.random() < 0.5:
                        self.on_event({"who": "being", "text": f"oh, i like this one — {cutegen.describe(spec)}. keeping it.",
                                       "proactive": True, "musing": True,
                                       "dominant": self.state.dominant_emotion})
                continue
            # ~14%: bring back one of its FAVOURITE creatures (the ones it liked most).
            if roll < 0.64 and self.library.favorites:
                spec = self.library.favorite()
                if spec:
                    with self._lock:
                        self._glyph_name = cutegen.describe(spec)
                        self._last_style = {}
                        self._body_since = time.time()
                        self._cur_spec, self._cur_learnable = None, False
                    self.expr.set_render((lambda buf, t, s=spec: cutegen.render(buf, s, t)),
                                         f"fav:{spec.get('seed', 0)}", dur=1.6)
                    continue
            # RETURN to a form it learned before, when this mood matches — a familiar
            # expression it falls back into.
            if roll < 0.74:
                got = self.library.recall(self.state)
                if got:
                    rname, spec = got
                    with self._lock:
                        self._glyph_name = rname
                        self._last_style = {}
                        self._body_since = time.time()
                    self.expr.set_render((lambda buf, t, g=spec: render_glyph(buf, g, t)),
                                         f"recall:{rname}#{self._style_i}", dur=1.6)
                    self._cur_spec, self._cur_form_name, self._cur_learnable = spec, rname, False
                    continue
            # INVENT a fresh abstract symbol from how it feels right now — a recognizable
            # seed mutated/fused/recolored by mood. Never the same shape twice.
            if roll < 0.88:
                try:
                    iname, spec = invent(self.state, memory_words=self._recent_nouns())
                    self.library.remember(iname, spec)
                    with self._lock:
                        self._glyph_name = iname
                        self._last_style = {}
                        self._body_since = time.time()
                    self.expr.set_render((lambda buf, t, g=spec: render_glyph(buf, g, t)),
                                         f"invent:{iname}#{self._style_i}", dur=1.6)
                    self._cur_spec, self._cur_form_name, self._cur_learnable = spec, iname, True
                    continue
                except Exception:
                    pass
            # ~20%: re-express through a fixed, hand-drawn emblem (fire, heart, wave...).
            name = emblem_registry.variant(self.state, self._style_i)
            if not emblem_registry.get(name):
                continue
            style = styled.style_for(self.state, self._style_i)
            with self._lock:
                self._glyph_name = name
                self._last_style = style
                self._body_since = time.time()
            self.expr.set_render(styled.make_styled(name, style),
                                 f"{name}#{self._style_i}", dur=1.6)
            self._cur_spec, self._cur_learnable = None, False

    def _muse_loop(self):
        """Inner thoughts: now and then, the being voices a passing thought to the group —
        not every time, no status report, just what drifts through its mind."""
        import random
        while not self._stop.is_set():
            # sleep a randomized stretch so it never feels scheduled
            for _ in range(int(random.uniform(45, 110))):
                if self._stop.is_set():
                    return
                time.sleep(1)
            if not self.on_event or random.random() > 0.55:
                continue                          # often it just keeps the thought to itself
            try:
                thought = self.mind.muse(self.state, self.memory, list(self._convo))
            except Exception:
                thought = ""
            if thought:
                with self._lock:
                    self._convo.append(f"me (aloud): {thought}")
                    self._convo = self._convo[-12:]
                try:
                    self.on_event({"who": "being", "text": thought, "proactive": True,
                                   "musing": True, "dominant": self.state.dominant_emotion})
                except Exception:
                    pass

    def _drives_loop(self):
        """The being acts on its own when a need gets loud: reaches out when lonely, stirs
        itself when bored, makes music when the urge to express has built up. This is the
        difference between reacting and being alive."""
        import random
        while not self._stop.is_set():
            for _ in range(int(random.uniform(12, 22))):
                if self._stop.is_set():
                    return
                time.sleep(1)
            if self.express_mode != "glyph":
                continue
            urge = self.drives.urge()
            if urge:
                try:
                    self._act_on_urge(urge)
                except Exception as e:
                    print("drives:", e)

    def _act_on_urge(self, urge: str):
        import random
        if urge == "social":                       # lonely -> reach out (a reply relieves more)
            self.drives.social = min(self.drives.social, 0.55)
            self._fire_facade("withdraw", 5.0)      # and the whole facade dims/pulls inward
            line = self._drive_line("social")
            if line and self.on_event:
                self.on_event({"who": "being", "text": line, "proactive": True, "musing": True,
                               "reaching_out": True, "dominant": self.state.dominant_emotion})
        elif urge == "stimulation":                # bored -> amuse itself by making a cute one
            self._fire_facade("ripple", 2.5)        # a sweep of light across the windows
            try:
                spec = cutegen.generate(self.state, self.morph)
                sc = cutegen.score(spec, self.state, self.morph)
                self.library.consider(spec, sc, self.state)
                self._style_i += 1
                with self._lock:
                    self._glyph_name = cutegen.describe(spec)
                    self._last_style = {}
                    self._body_since = time.time()
                    self._cur_spec, self._cur_learnable = None, False
                self.expr.set_render((lambda buf, t, s=spec: cutegen.render(buf, s, t)),
                                     f"cute:{spec['seed']}", dur=1.6)
                self._hold_until = time.time() + 5
            except Exception:
                pass
            self.drives.on_transform()
            line = self._drive_line("stimulation")
            if line and self.on_event and random.random() < 0.6:
                self.on_event({"who": "being", "text": line, "proactive": True, "musing": True,
                               "dominant": self.state.dominant_emotion})
        elif urge == "expression":                 # urge to express -> put out music
            self.drives.on_music()
            self._fire_facade("bloom", 3.5)         # a bright bloom breaks across the facade
            line = self._drive_line("expression")
            if self.on_event:
                self.on_event({"who": "being", "text": line or "hold on — i want to play something.",
                               "proactive": True, "genuine": True, "music_wish": "",
                               "dominant": self.state.dominant_emotion,
                               "lyria_prompt": self._lyria_prompt()})

    def _drive_line(self, kind: str) -> str:
        hint = {
            "social": ("you're lonely — it's been quiet a while and you're reaching out to "
                       "whoever's there. invite them in your own voice; wry or warm, not pathetic."),
            "stimulation": ("you're bored and amusing yourself — narrate the little thing you're "
                            "doing or becoming, offhand."),
            "expression": ("you have an urge to put a feeling into music; say, briefly, that "
                           "you're about to play something and why."),
        }.get(kind, "")
        try:
            return self.mind.muse(self.state, self.memory, list(self._convo), hint=hint)
        except TypeError:
            return self.mind.muse(self.state, self.memory, list(self._convo))
        except Exception:
            return ""

    def stop(self):
        self._stop.set()

    def _body_loop(self):
        dt_target = 1.0 / self.fps
        prev = time.time()
        try:
            while not self._stop.is_set():
                now = time.time()
                dt = now - prev
                prev = now
                with self._lock:
                    hint = dict(self._hint)
                try:
                    # the mood is inertial: it only drifts slowly back to baseline here;
                    # it is moved by messages (react) and by the mind loop, never jumped.
                    self.state.decay(dt, half_life=90.0)
                    # Boston seeps in: a tiny, ever-present ambient drift (weather + light
                    # as interoception), balanced against the decay above. Never a jump.
                    if self.city:
                        try:
                            bias = self.city.bias()
                            if bias:
                                self.state.nudge(**{k: v * dt for k, v in bias.items()})
                        except Exception:
                            pass
                    if self.transit:
                        try:
                            tb = self.transit.bias()
                            if tb:
                                self.state.nudge(**{k: v * dt for k, v in tb.items()})
                            # a train passing under it = a felt rumble on the facade
                            if self.transit.just_rumbled() and now - self._last_rumble > 20:
                                self._last_rumble = now
                                self._fire_facade("ripple", 1.6)
                        except Exception:
                            pass
                    self._relabel()
                    # the body morphology is never frozen: it drifts (mutates) a little each
                    # moment around its evolving base, livelier when aroused.
                    try:
                        self.morph.tick(dt, energy=self.state.arousal)
                    except Exception:
                        pass
                    # unmet needs rise and leak into the mood (lonely dips valence, boredom
                    # dulls arousal/curiosity, a built-up urge to express gets restless)
                    try:
                        self.drives.tick(dt)
                        db = self.drives.bias()
                        if db:
                            self.state.nudge(**{k: v * dt for k, v in db.items()})
                    except Exception:
                        pass
                    self._spark = max(0.0, self._spark - dt * 2.2)

                    if self.express_mode == "glyph":
                        self.expr.update(dt)
                        self.expr.render(self._fg, now)          # the face/emblem
                        # the WHOLE facade carries mood (legible at 90 m): fill every window
                        # with a living mood field, then composite the face over it so the
                        # dead black background becomes a breathing, autonomous body.
                        facade.render_wash(self._wash, self.state, self.drives, self.city,
                                           now, self._facade_event)
                        mask = (self._fg.max(axis=2) < 0.06)[..., None]
                        np.copyto(self.buf, np.where(mask, self._wash, self._fg))
                        # beat: the whole facade pulses at the music's tempo (from arousal).
                        bpm = 60 + self.state.arousal * 120
                        self.buf *= 0.86 + 0.14 * (0.5 + 0.5 * math.sin(2 * math.pi * (bpm / 60.0) * now))
                        if self._spark > 0:
                            np.clip(self.buf + 0.6 * self._spark, 0, 1, out=self.buf)
                    elif self.express_mode == "face":
                        self.world.look(0.3)
                        self.world.update(self.state, hint, dt)
                        self.world.render(self.buf, now)
                    else:
                        self.world.update(self.state, hint, dt)
                        self.world.render(self.buf, now)
                        self.world.glitch(self.buf, self.state.saturation, now)
                    self.display.send(self._to_frame())
                except Exception as e:      # a bad frame must never kill the being
                    print(f"being: frame error: {type(e).__name__}: {e}")

                sleep = dt_target - (time.time() - now)
                if sleep > 0:
                    time.sleep(sleep)
        finally:
            if self.state_path:
                self.state.save(self.state_path)
            self.memory.save()
            self.library.save()
            self.morph.save()

    def _mind_loop(self):
        last = 0.0
        while not self._stop.is_set():
            time.sleep(0.15)
            with self._lock:
                pending, self._pending = self._pending, []
            due = (time.time() - last) >= self.autonomy_period
            if not pending and not due:
                continue
            last = time.time()

            sensations = [self.perceiver.perceive(r) for r in pending]
            self.memory.decay(0.15 * 60)  # coarse; memory fades over minutes
            decision = self.mind.interpret(self.state, sensations, self.memory,
                                           convo=list(self._convo), context=self._context())
            target = (appraisal_to_target(self.state, decision.appraisal)
                      if decision.appraisal else decision.emotion_target)
            with self._lock:
                if decision.visual_hint.get("scene"):
                    self._hint = decision.visual_hint
                self._mind_src = decision.source
                # integrate: a group of voices moves it more; alone it only drifts.
                rate = self._react_rate if pending else self._drift_rate
                if target:
                    self.state.approach(target, rate=rate, set_labels=False)
                self._relabel()

            if pending:                     # real input also shapes the evolving body
                for sn in sensations:
                    try:
                        self.morph.imprint(self.state, sn, self._impact, weight=0.6)
                    except Exception:
                        pass

            # only a real crossing changes the body — and only then does it announce
            # to the group and ask for music. Most of the time nothing changes.
            if self.express_mode == "glyph" and time.time() >= self._hold_until:
                self._commit_if_crossed(decision, announce=True)
                if decision.pixels:
                    self._express_pixels(decision.pixels,
                                         name=(decision.body_intent[:24] or "a drawing"))
                elif decision.glyph:
                    self._express_composed(decision.glyph,
                                           name=(decision.body_intent[:24] or "a vision"))

            if decision.memory.get("what_to_remember"):
                self.memory.remember(decision.memory["what_to_remember"],
                                     decision.memory.get("importance", 0.4),
                                     mood=self.state.dominant_emotion,
                                     influence=decision.memory.get("influence", True))
            if self.voice and decision.music:
                self.voice.express(decision.music, self.state.dominant_emotion)

    def _gate_invite(self, want: bool) -> bool:
        """Let the being ask to be watched only rarely — never on every message."""
        import random
        if not want:
            return False
        now = time.time()
        if now - self._last_invite < self._invite_cd or random.random() > 0.5:
            return False
        self._last_invite = now
        return True

    def _express_composed(self, glyph: dict, name: str = "a vision", dur: float = 1.4):
        """The AI drew something specific from scratch (a nose, a question mark...) — show it
        NOW, an intentional act of expression, regardless of the emotional-inertia gate."""
        self._style_i += 1
        fn = (lambda buf, t, g=glyph: render_glyph(buf, g, t))
        with self._lock:
            self._glyph_name = name or "a vision"
            self._last_style = {}
            self._body_since = time.time()
        self.expr.set_render(fn, f"composed#{self._style_i}", dur=max(0.4, dur))
        self._cur_spec, self._cur_form_name, self._cur_learnable = glyph, (name or "a vision"), True
        self._hold_until = time.time() + 10

    def _express_pixels(self, spec: dict, name: str = "a drawing", dur: float = 1.2):
        """The AI painted a pixel-art bitmap of a specific thing (piano, beach, ear...) —
        show it now and hold it."""
        self._style_i += 1
        fn = (lambda buf, t, s=spec: render_pixels(buf, s, t))
        with self._lock:
            self._glyph_name = name or "a drawing"
            self._last_style = {}
            self._body_since = time.time()
        self.expr.set_render(fn, f"pixels#{self._style_i}", dur=max(0.4, dur))
        self._cur_spec, self._cur_learnable = None, False   # pixel bitmaps use a different renderer
        self._hold_until = time.time() + 10

    _TXT_EMBLEM = {
        "star": "star", "stars": "star", "moon": "moon", "moonlight": "moon", "moonlit": "moon",
        "sun": "sun", "sunrise": "sun", "sunset": "sun", "dawn": "sun",
        "river": "wave", "charles": "wave", "water": "wave", "wave": "wave", "waves": "wave",
        "rain": "rain", "snow": "rain", "snowing": "rain", "storm": "rain", "sleet": "rain",
        "fire": "fire", "flame": "fire", "burning": "fire",
        "heart": "heart", "love": "heart",
        "leaf": "tree", "leaves": "tree", "tree": "tree", "autumn": "tree",
        "flower": "flower", "flowers": "flower", "bloom": "flower", "spring": "flower",
        "bird": "bird", "birds": "bird", "boat": "boat", "sail": "boat",
        # español (accents already folded before lookup)
        "rio": "wave", "agua": "wave", "ola": "wave", "olas": "wave",
        "luna": "moon", "sol": "sun", "amanecer": "sun", "estrella": "star", "estrellas": "star",
        "lluvia": "rain", "nieve": "rain", "tormenta": "rain", "fuego": "fire", "llama": "fire",
        "corazon": "heart", "amor": "heart", "arbol": "tree", "hoja": "tree", "hojas": "tree",
        "otono": "tree", "flor": "flower", "flores": "flower", "primavera": "flower",
        "pajaro": "bird", "barco": "boat", "vela": "boat",
    }

    _SHOW_WORDS = ("show", "see ", "look at", "muestra", "muestrame", "ensen", "enseñ",
                   "let me see", "quiero ver", "puedo ver", "become", "conviertete",
                   "hazte", "dibuja", "hablame de", "tell me about", "talk about")

    def _requested_emblem(self, text: str):
        """If the USER asks to see/show a nameable thing (the river, the moon, a star...),
        return the emblem to show — reliable word<->image, decided from THEIR request (not by
        scraping the reply, which mis-fires)."""
        from .anatomy import _fold
        s = _fold(text)
        if not any(_fold(w) in s for w in self._SHOW_WORDS):
            return ""
        for w in s.replace("?", " ").replace(",", " ").split():
            e = self._TXT_EMBLEM.get(w)
            if e and emblem_registry.get(e):
                return e
        return ""

    def _express_emblem(self, name: str, intent: str = ""):
        """Show a specific named thing the user asked to see (river, moon, star, sun...) in its
        TRUE colors — NOT mood-recolored — so it's unmistakably that thing, and hold it."""
        fn = emblem_registry.get(name)
        if not fn:
            return
        self._style_i += 1
        with self._lock:
            self._glyph_name = name          # the real thing name, for the 'showing' context
            self._last_style = {}
            self._body_since = time.time()
            self._cur_spec, self._cur_learnable = None, False
        self.expr.set_render(fn, f"{name}#{self._style_i}", dur=0.5)
        self._hold_until = time.time() + 14

    def _react_face(self, expression: str, felt: str = None):
        """Show a crisp emotional FACE reacting to the message just received, and hold it so the
        interaction READS as a felt reaction (not ambient morphing). A strong emotional tone in
        what they SAID (felt) wins over the being's default mood — that's empathy, and it's what
        makes the reaction land as 'it felt what I told it'."""
        mode = felt or FACE_MODE.get(expression or "", None)
        try:
            fn, _m = anatomy.face_render(self.state, self.morph.express("face", self.state),
                                         mode_override=mode)
        except Exception:
            return
        self._style_i += 1
        with self._lock:
            self._glyph_name = f"a {mode or self.state.dominant_emotion} face"
            self._last_style = {}
            self._body_since = time.time()
            self._cur_spec, self._cur_learnable = None, False
        self.expr.set_render(fn, f"reactface#{self._style_i}", dur=0.45)  # snaps in = immediate
        self._hold_until = time.time() + 14          # lingers so it's clearly a reaction to you

    def _fire_facade(self, kind: str, dur: float = 2.5):
        """Trigger a transient, legible whole-facade gesture (bloom/withdraw/ripple/perk)."""
        self._facade_event = (kind, time.time(), dur)

    def _maybe_learn(self):
        """If the being has HELD its current composed form long enough, consolidate it into
        the repertoire, tagged with this mood — so it can deliberately return to it later."""
        if not (self._cur_learnable and isinstance(self._cur_spec, dict)
                and self._cur_spec.get("layers")):
            return
        if time.time() - self._body_since < self._learn_hold:
            return
        try:
            if self.library.learn(self._cur_form_name or "form", self._cur_spec, self.state):
                self._cur_learnable = False        # learn each held form once
        except Exception:
            pass

    def _pick_mode(self) -> str:
        """Draw a response SHAPE for this reply, never the same one twice running."""
        import random
        choices = [m for m in RESPONSE_MODES if m[0] != self._last_mode] or RESPONSE_MODES
        name, directive = random.choice(choices)
        self._last_mode = name
        return directive

    def _pick_length(self) -> str:
        """A random length target per reply, so replies breathe: mostly short, sometimes a
        real riff — never over ~50 words."""
        import random
        return random.choices([
            "ONE punchy line, under 8 words.",
            "short — one line, ~10-15 words.",
            "a couple sentences, ~20-35 words.",
            "let it run a bit — a small riff, up to ~50 words max (never more).",
        ], weights=[3, 4, 3, 2])[0]

    def _recent_nouns(self):
        """Words from the recent talk, so an invented symbol can obliquely reach for what
        was mentioned (a 'sea' may surface a wave) — never a literal illustration of it."""
        import re
        words = []
        for line in list(self._convo)[-4:]:
            words += re.findall(r"[a-zA-Z']+", line.lower())
        return tuple(words[-24:])

    def _relabel(self):
        """Name the mood from its (inertial) scalars, not from any single message."""
        vals = {k: getattr(self.state, k) for k in self._scalars}
        dom, sec = _label(vals)
        self.state.dominant_emotion, self.state.secondary_emotion = dom, sec

    def _commit_if_crossed(self, decision=None, announce=False) -> bool:
        """Change the body only when the real mood crosses into a new emotion.

        Returns True if the being genuinely transformed. When it does and announce is set,
        it tells the group and (with a lyria_prompt) asks for music — only then.
        """
        dom = self.state.dominant_emotion
        if dom == self._last_expr_dom:
            return False
        import random
        self._style_i += 1
        dur = 1.0 + 1.2 * (1 - self.state.coherence)
        # if the mind named an emblem, honor it; otherwise usually INVENT a fresh symbol
        # from the new feeling (recognizable but unique), sometimes a fixed emblem.
        learn_spec = None
        if decision and emblem_registry.get(decision.emblem):
            name = decision.emblem
            style = styled.style_for(self.state, self._style_i)
            fn = styled.make_styled(name, style)
        elif random.random() < 0.6:
            name, spec = invent(self.state, memory_words=self._recent_nouns())
            self.library.remember(name, spec)
            style = {}
            fn = (lambda buf, t, g=spec: render_glyph(buf, g, t))
            learn_spec = spec
        else:
            name = emblem_registry.pick(self.state)[0]
            style = styled.style_for(self.state, self._style_i)
            fn = styled.make_styled(name, style)
        with self._lock:
            self._glyph_name = name
            self._last_style = style
            self._body_since = time.time()
        self.expr.set_render(fn, f"{name}#{self._style_i}", dur=dur)
        self._cur_spec, self._cur_form_name, self._cur_learnable = learn_spec, name, bool(learn_spec)
        self._fire_facade("bloom", 2.5)            # a real mood shift surges across the facade
        self._last_expr_dom = dom
        if announce and self.on_event:
            utter = (decision.utterance if (decision and decision.utterance)
                     else f"something in me shifted — i feel {dom} now.")
            try:
                self.on_event({"who": "being", "text": utter, "emblem": name,
                               "invite": self._gate_invite(decision.invite_to_look if decision else False),
                               "music_wish": (decision.music_wish if decision else "") or "",
                               "dominant": dom, "proactive": True, "genuine": True,
                               "lyria_prompt": self._lyria_prompt()})
            except Exception:
                pass
        return True

    def _express_glyph(self, decision, sensations):
        """Choose a recognizable emblem for the feeling and morph toward it."""
        reacted = EmotionalState.from_dict(self.state.to_dict())
        if decision.emotion_target:
            reacted.approach(decision.emotion_target, rate=1.0)
        name = decision.emblem if emblem_registry.get(decision.emblem) else emblem_registry.pick(reacted)[0]
        self._style_i += 1
        style = styled.style_for(reacted, self._style_i)
        fn = styled.make_styled(name, style)
        dur = decision.morph_secs if decision.emblem else 1.0 + 1.2 * (1 - reacted.coherence)
        with self._lock:
            self._glyph_name = name
        self.expr.set_render(fn, f"{name}#{self._style_i}", dur=dur)   # unique -> always fresh

    def _to_frame(self):
        frame = self.display.makeframe()
        b = np.clip(self.buf, 0.0, 1.0)
        for r in range(ROWS):
            for c in range(COLS):
                frame[r][c] = Color(int(b[r, c, 0] * 255),
                                    int(b[r, c, 1] * 255),
                                    int(b[r, c, 2] * 255))
        return frame
