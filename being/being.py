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
from .inventor import Library
from . import emblem_registry, styled, gestures
from .glyph import render_glyph, render_pixels


class Being:
    def __init__(self, display, mind=None, voice=None, state_path="", memory_path="",
                 fps=30, autonomy_period=7.0, time_of_day=0.5, express_mode="glyph",
                 library_path="", view_url="", on_event=None):
        self.view_url = view_url
        self.on_event = on_event      # called with a dict when the being speaks to the group
        self.display = display
        self.mind = mind or make_mind()
        self.voice = voice
        self.fps = fps
        self.autonomy_period = autonomy_period
        self.express_mode = express_mode      # "glyph" (emblems), "world" (Zelda), "face"

        self.state = EmotionalState.load(state_path) if state_path else EmotionalState()
        self.memory = Memory(memory_path) if memory_path else Memory("/tmp/gb_mem.json")
        self.state_path = state_path
        self.perceiver = Perceiver()
        self.world = ZeldaWorld(time_of_day=time_of_day)
        self.expr = Expression()              # glyph metamorphosis engine
        self.library = Library(library_path)  # invented emblems, grows with interaction
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
        self._scalars = ("arousal", "valence", "curiosity", "openness", "confidence",
                         "saturation", "social_affinity", "coherence")
        self.buf = np.zeros((ROWS, COLS, 3), dtype=float)
        self._lock = threading.Lock()
        self._pending = []                 # raw stimuli awaiting the mind
        self._target = None                # emotional target the body eases toward
        self._hint = {}
        self._approach = 1.6
        self._stop = threading.Event()
        self._mind_src = self.mind.__class__.__name__
        self._last_line = ""
        if self.express_mode == "glyph":          # something to show before the first thought
            nm, _ = emblem_registry.pick(self.state)
            self._glyph_name = nm
            self._last_expr_dom = self.state.dominant_emotion
            self.expr.set_render(styled.make_styled(nm, styled.style_for(self.state, 0)), nm + "#0")

    def _context(self) -> dict:
        """What the being knows about its own body + how it's landing — fed to the mind so
        it can talk about how it looks, choose what to express, and read its impact."""
        held = int(time.time() - self._body_since)
        orn = (self._last_style or {}).get("ornament", "plain")
        body = (f"a {self._glyph_name or 'shape'} with {orn} accents, expressing your "
                f"{self.state.dominant_emotion} mood, held for {held}s")
        imp = ("really landing" if self._impact > 0.62 else
               "barely landing / they seem distant" if self._impact < 0.42 else "landing okay")
        return {"body": body, "impact": imp}

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

        # If they asked to SEE a body part / gesture, show it on the screen INSTANTLY —
        # before the language model even answers. The screen is the body.
        gname = gestures.detect(text) if self.express_mode == "glyph" else None
        if gname:
            self._style_i += 1
            with self._lock:
                self._glyph_name = gname
                self._body_since = time.time()
                self._last_style = {}
            self.expr.set_render(gestures.make_gesture(gname, self.state),
                                 f"gesture:{gname}#{self._style_i}", dur=0.5)
            self._hold_until = time.time() + 10   # keep it up so they can actually see it

        decision = self.mind.interpret(self.state, [sens], self.memory,
                                       speaker=speaker, convo=convo, context=self._context())
        # its expressions landing well/poorly is a feedback signal it can feel
        self._impact = 0.82 * self._impact + 0.18 * sens.valence_tone
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
            self._relabel()
        # The body changes only if that nudge actually tipped the being into a new mood;
        # otherwise it just answers with words and keeps the body it already wears.
        if gname:
            body_changed = True                    # already showing the requested gesture; keep it
        elif self.express_mode == "glyph" and decision.pixels:   # the AI painted a specific thing
            self._express_pixels(decision.pixels,
                                 name=(decision.body_intent[:24] or "a drawing"))
            body_changed = True
        elif self.express_mode == "glyph" and decision.glyph:   # the AI drew with primitives
            self._express_composed(decision.glyph,
                                   name=(decision.body_intent[:24] or decision.emblem or "a vision"),
                                   dur=decision.morph_secs)
            body_changed = True
        elif self.express_mode == "glyph" and time.time() >= self._hold_until:
            body_changed = self._commit_if_crossed(decision, announce=False)
        else:
            body_changed = False
        if decision.utterance:
            with self._lock:
                self._convo.append(f"me: {decision.utterance}")
                self._convo = self._convo[-12:]
        m = decision.memory or {}
        if m.get("what_to_remember"):
            self.memory.remember(m["what_to_remember"], m.get("importance", 0.4),
                                 mood=self.state.dominant_emotion, influence=m.get("influence", True))

        it = (decision.structured or {}).get("interpretation") or {}
        SCAL = self._scalars
        lp = lyria_prompt(self.state)
        if decision.music_wish:
            lp = decision.music_wish + " — " + lp
        music_req = any(w in text.lower() for w in (
            "music", "song", "sing", "play me", "play a", "tune", "beat", "melod",
            "canción", "cancion", "música", "musica", "suena", "tócame", "tocame", "toca "))
        wants_music = bool(body_changed or music_req)
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
            "music_wish": decision.music_wish or "",
            "source": decision.source,
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
                "repertoire": len(self.library)}

    def status(self) -> str:
        if self.express_mode == "glyph":
            return (f"[{self._glyph_name or '...'}] {self.state.summary()} "
                    f"| mind:{self._mind_src} | repertoire:{len(self.library)} "
                    f"| last:{self._last_line[:20]}")
        return (f"[{self.world.biome}] {self.state.summary()} "
                f"| mind:{self._mind_src} | last:{self._last_line[:24]}")

    # -- run ----------------------------------------------------------------
    def run(self):
        mt = threading.Thread(target=self._mind_loop, name="being-mind", daemon=True)
        mt.start()
        threading.Thread(target=self._muse_loop, name="being-muse", daemon=True).start()
        threading.Thread(target=self._refresh_loop, name="being-refresh", daemon=True).start()
        self._body_loop()

    def _refresh_loop(self):
        """Keep the body looking alive and NEW: every so often the being re-expresses its
        current mood as a fresh variation (new colors, ornament, sometimes a sibling
        emblem) with a visible morph — without changing how it feels."""
        import random
        while not self._stop.is_set():
            for _ in range(int(random.uniform(13, 26))):   # change more often, feel alive
                if self._stop.is_set():
                    return
                time.sleep(1)
            if self.express_mode != "glyph" or self.expr.transforming:
                continue
            if time.time() < self._hold_until:     # a requested gesture/drawing is on screen
                continue
            self._style_i += 1
            # ~half the time show a LIVING gesture (a face that blinks, an eye that looks
            # around, a wave, a little walk) instead of an abstract emblem — so passively
            # watching the building feels like a creature, not the same shapes on loop.
            if random.random() < 0.5:
                gname = random.choices(["face", "eye", "wave", "walk"],
                                       weights=[5, 2, 2, 2])[0]
                with self._lock:
                    self._glyph_name = gname
                    self._last_style = {}
                    self._body_since = time.time()
                self.expr.set_render(gestures.make_gesture(gname, self.state),
                                     f"gesture:{gname}#{self._style_i}", dur=1.6)
                continue
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
                    self._relabel()
                    self._spark = max(0.0, self._spark - dt * 2.2)

                    if self.express_mode == "glyph":
                        self.expr.update(dt)
                        self.expr.render(self.buf, now)
                        # beat: pulse the body at the tempo of the music it's making
                        # (both derive from arousal), so the building throbs in time.
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
        self._hold_until = time.time() + 10

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
        name = (decision.emblem if (decision and emblem_registry.get(decision.emblem))
                else emblem_registry.pick(self.state)[0])
        self._style_i += 1
        style = styled.style_for(self.state, self._style_i)
        dur = 1.0 + 1.2 * (1 - self.state.coherence)
        with self._lock:
            self._glyph_name = name
            self._last_style = style
            self._body_since = time.time()
        self.expr.set_render(styled.make_styled(name, style), f"{name}#{self._style_i}", dur=dur)
        self._last_expr_dom = dom
        if announce and self.on_event:
            from .music import lyria_prompt
            utter = (decision.utterance if (decision and decision.utterance)
                     else f"something in me shifted — i feel {dom} now.")
            try:
                self.on_event({"who": "being", "text": utter, "emblem": name,
                               "invite": self._gate_invite(decision.invite_to_look if decision else False),
                               "music_wish": (decision.music_wish if decision else "") or "",
                               "dominant": dom, "proactive": True, "genuine": True,
                               "lyria_prompt": lyria_prompt(self.state)})
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
