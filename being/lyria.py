"""Google Lyria music generation (via the Gemini API).

The being's feeling becomes a text prompt; Lyria 3.5 returns an instrumental clip
(audio/mpeg). This is the being's voice — music generated live from the interaction.
Reads GEMINI_KEY (or GOOGLE_API_KEY) from the environment; degrades to None with no key.
"""
from __future__ import annotations
import json
import os
import urllib.request

_MODEL = os.environ.get("LYRIA_MODEL", "lyria-3.5")
_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"


def have_key() -> bool:
    return bool(os.environ.get("GEMINI_KEY") or os.environ.get("GOOGLE_API_KEY"))


def generate(prompt: str, timeout: float = 40.0) -> dict | None:
    """Return {"mime": "audio/mpeg", "b64": "..."} or None on failure/no key."""
    key = os.environ.get("GEMINI_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        return None
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode()
    req = urllib.request.Request(
        _URL.format(model=_MODEL, key=key), data=body,
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.load(resp)
        for part in data["candidates"][0]["content"]["parts"]:
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and "data" in inline:
                return {"mime": inline.get("mimeType", "audio/mpeg"), "b64": inline["data"]}
    except Exception as e:
        print(f"lyria: generation failed: {type(e).__name__}: {e}")
    return None
