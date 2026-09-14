"""Minimal Telegram Bot client (stdlib only): long-poll updates, send text, and upload
the being's body image (PNG) and its generated music (MP3). No external packages.
"""
from __future__ import annotations
import io
import json
import os
import urllib.parse
import urllib.request


class Telegram:
    def __init__(self, token: str):
        self.base = f"https://api.telegram.org/bot{token}"

    def _get(self, method: str, params: dict | None = None, timeout: float = 35):
        url = self.base + "/" + method
        if params:
            url += "?" + urllib.parse.urlencode(params)
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.load(r)

    def _post_multipart(self, method: str, fields: dict, files: dict, timeout: float = 90):
        boundary = "----gb" + os.urandom(8).hex()
        body = io.BytesIO()
        for k, v in fields.items():
            body.write(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
        for k, (fn, data, ctype) in files.items():
            body.write(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"; filename="{fn}"\r\n'
                       f'Content-Type: {ctype}\r\n\r\n'.encode())
            body.write(data)
            body.write(b"\r\n")
        body.write(f"--{boundary}--\r\n".encode())
        req = urllib.request.Request(self.base + "/" + method, data=body.getvalue(),
                                     headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)

    def get_me(self):
        return self._get("getMe", timeout=15)

    def get_updates(self, offset: int, timeout: int = 30):
        return self._get("getUpdates", {"offset": offset, "timeout": timeout}, timeout=timeout + 8)

    def send_message(self, chat_id, text: str):
        try:
            return self._get("sendMessage", {"chat_id": chat_id, "text": text[:4000]}, timeout=20)
        except Exception as e:
            print("telegram send_message failed:", e)

    def send_photo(self, chat_id, png: bytes, caption: str = ""):
        try:
            return self._post_multipart("sendPhoto",
                                        {"chat_id": str(chat_id), "caption": caption[:900]},
                                        {"photo": ("body.png", png, "image/png")})
        except Exception as e:
            print("telegram send_photo failed:", e)

    def send_audio(self, chat_id, mp3: bytes, caption: str = ""):
        try:
            return self._post_multipart("sendAudio",
                                        {"chat_id": str(chat_id), "caption": caption[:900],
                                         "title": "the being", "performer": "MIT Green Building"},
                                        {"audio": ("being.mp3", mp3, "audio/mpeg")})
        except Exception as e:
            print("telegram send_audio failed:", e)
