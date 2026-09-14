"""MUSICAL VOICE: the being's feelings become a short phrase of tones.

This is a coupled expression of the same state that paints the world, not a reaction
to the human's words. It writes a small WAV and plays it with macOS `afplay` in the
background; with no audio available it degrades silently. Phrases are debounced so the
being does not chatter over itself.
"""
from __future__ import annotations
import math
import os
import shutil
import struct
import subprocess
import tempfile
import time
import wave

_SR = 22050

# scales chosen by how consonant / ordered the being feels
_MAJOR_PENT = [0, 2, 4, 7, 9]
_MINOR_PENT = [0, 3, 5, 7, 10]
_WHOLE_TONE = [0, 2, 4, 6, 8, 10]


class Voice:
    def __init__(self, enabled: bool = True, min_gap: float = 1.6):
        self.enabled = enabled and shutil.which("afplay") is not None
        self.min_gap = min_gap
        self._last = 0.0
        self._proc = None

    def express(self, music: dict, mood: str = ""):
        if not self.enabled:
            return
        now = time.time()
        if now - self._last < self.min_gap:
            return
        self._last = now
        try:
            path = self._render(music)
            if self._proc and self._proc.poll() is None:
                self._proc.terminate()
            self._proc = subprocess.Popen(["afplay", path],
                                          stdout=subprocess.DEVNULL,
                                          stderr=subprocess.DEVNULL)
        except Exception:
            pass  # a voice that cracks is not a crash

    def _render(self, m: dict) -> str:
        tempo = float(m.get("tempo", 0.4))
        density = float(m.get("density", 0.5))
        register = float(m.get("register", 0.5))
        consonance = float(m.get("consonance", 0.6))
        dynamics = float(m.get("dynamics", 0.5))
        contour = str(m.get("contour", "wander"))

        scale = (_MAJOR_PENT if consonance > 0.6 else
                 _MINOR_PENT if consonance > 0.35 else _WHOLE_TONE)
        n_notes = max(2, int(2 + density * 6))
        note_dur = max(0.09, 0.28 - 0.16 * tempo)
        root = 48 + int(register * 24)      # MIDI, ~C3..C5

        degrees = []
        idx = 0
        for i in range(n_notes):
            if contour == "rising":
                idx += 1
            elif contour == "falling":
                idx -= 1
            elif contour == "arch":
                idx += 1 if i < n_notes / 2 else -1
            elif contour == "static":
                idx = 0
            else:
                idx += (1 if (i * 7 + 3) % 3 else -1)
            degrees.append(idx)

        amp = 0.18 + 0.5 * dynamics
        samples = bytearray()
        for d in degrees:
            octave, step = divmod(d, len(scale))
            midi = root + 12 * octave + scale[step % len(scale)]
            freq = 440.0 * (2 ** ((midi - 69) / 12.0))
            samples += self._tone(freq, note_dur, amp,
                                  harsh=(consonance < 0.35))
        return self._write(samples)

    def _tone(self, freq, dur, amp, harsh=False):
        n = int(_SR * dur)
        out = bytearray()
        for i in range(n):
            t = i / _SR
            env = min(1.0, t / 0.01) * min(1.0, (dur - t) / 0.05)  # soft attack/release
            v = math.sin(2 * math.pi * freq * t)
            if harsh:
                v = 0.6 * v + 0.4 * math.sin(2 * math.pi * freq * 1.5 * t)  # dissonant fifth-ish
            s = int(max(-1, min(1, v * env * amp)) * 32767)
            out += struct.pack("<h", s)
        return out

    def _write(self, samples: bytes) -> str:
        fd, path = tempfile.mkstemp(suffix=".wav", prefix="gb_voice_")
        os.close(fd)
        with wave.open(path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(_SR)
            w.writeframes(bytes(samples))
        return path
