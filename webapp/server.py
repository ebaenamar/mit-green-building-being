#!/usr/bin/env python3
"""Web app: people chat with the being; they see its sentiment, hear the music it
generates (Google Lyria), and it can beckon them to watch its body (the building).

  OPENAI_API_KEY=... GEMINI_KEY=... EVENT_PASSWORD=... python3 webapp/server.py
  # or reuse an instance:  GB_INSTANCE=witty-koala ... python3 webapp/server.py

Env:
  OPENAI_API_KEY  the being's mind (falls back to reflex mind if unset)
  GEMINI_KEY      Google Lyria music (falls back to in-browser synth if unset)
  EVENT_PASSWORD  to mint a fresh building instance (else set GB_INSTANCE)
  GB_INSTANCE     reuse an existing instance name
  GB_BASE         sim API base (default https://sundai.willsarg.com/api)
  PORT            default 8010
"""
import base64
import json
import os
import sys
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gbsim import WebDisplay
from being.being import Being
from being.mind import make_mind
from being.city import CitySense
from being.transit import TransitSense
from being import lyria, pngutil
from being.telegram import Telegram

BASE = os.environ.get("GB_BASE", "https://sundai.willsarg.com/api")
HERE = os.path.dirname(os.path.abspath(__file__))

# shared group feed: everyone sees the same conversation, including the being's own posts
FEED = []
_FEED_LOCK = threading.Lock()


def push(ev: dict):
    with _FEED_LOCK:
        ev = dict(ev)
        ev["id"] = len(FEED)
        FEED.append(ev)
        del FEED[:-400]


# live viewer count: distinct clients polling the body in the last few seconds
_VIEWERS = {}
_VIEW_LOCK = threading.Lock()


def _seen_viewer(ip):
    now = time.time()
    with _VIEW_LOCK:
        _VIEWERS[ip] = now
        for k in [k for k, ts in _VIEWERS.items() if now - ts > 8]:
            del _VIEWERS[k]
        n = len(_VIEWERS)
    try:
        BEING.viewers = n
    except Exception:
        pass


def make_instance():
    name = os.environ.get("GB_INSTANCE")
    if name:
        return name
    pw = os.environ.get("EVENT_PASSWORD")
    if not pw:
        sys.exit("Set GB_INSTANCE=<name> or EVENT_PASSWORD=<pw> to mint one.")
    req = urllib.request.Request(BASE + "/instances",
                                 data=json.dumps({"password": pw}).encode(),
                                 headers={"Content-Type": "application/json",
                                          "User-Agent": "gbsim/1"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.load(r)["name"]


NAME = make_instance()
VIEW = BASE.rsplit("/api", 1)[0] + "/" + NAME
DISPLAY = WebDisplay(NAME, base_url=BASE)
# Boston's live weather + light, folded into the being as interoception (disable with
# GB_CITY=off). No API key needed (Open-Meteo); falls back to a synthetic sky offline.
CITY = None if os.environ.get("GB_CITY", "").lower() in ("off", "0", "no") else CitySense()
# the Red Line at Kendall/MIT, felt under the building (disable with GB_TRANSIT=off)
TRANSIT = None if os.environ.get("GB_TRANSIT", "").lower() in ("off", "0", "no") else TransitSense()
BEING = Being(DISPLAY, mind=make_mind(prefer_llm=True), voice=None,
              memory_path=os.path.join(HERE, "..", "data", "web_mem.json"),
              library_path=os.path.join(HERE, "..", "data", "web_glyphs.json"),
              genome_path=os.path.join(HERE, "..", "data", "web_morph.json"),
              express_mode="glyph", view_url=VIEW, on_event=push, city=CITY, transit=TRANSIT,
              fps=int(os.environ.get("GB_FPS", "15")),   # lower fps frees the GIL for chat requests
              autonomy_period=float(os.environ.get("GB_AUTONOMY", "26")))
threading.Thread(target=BEING.run, name="being", daemon=True).start()

# ---- Telegram group channel (optional) -----------------------------------
TG_TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
TG = Telegram(TG_TOKEN) if TG_TOKEN else None
CHATS = set()


def _emblem_png(scale=54):
    fr = BEING.current_frame()
    return pngutil.encode_scaled(fr["cells"], fr["w"], fr["h"], scale)


def tg_reply(chat, r):
    txt = r.get("utterance") or r.get("feels") or "…"
    line = txt
    if r.get("invite_to_look"):
        line += f"\n👁 look at my body: {VIEW}"
    # human cadence: show "typing…" and pause a beat scaled by its mood before replying
    try:
        TG.send_chat_action(chat, "typing")
        time.sleep(min(4.0, max(0.0, float(r.get("reply_delay", 1.0) or 1.0))))
    except Exception:
        pass
    TG.send_message(chat, line)
    # Show a new body image when it changed/drew; send music when it changed OR they
    # asked for it — so music actually flows.
    if r.get("body_changed"):
        time.sleep(1.4)   # let the shape finish morphing in before we photograph it
        try:
            TG.send_photo(chat, _emblem_png(), caption=r.get("glyph") or "")
        except Exception as e:
            print("tg photo:", e)
    if r.get("wants_music") and lyria.have_key() and r.get("lyria_prompt"):
        a = lyria.generate(r["lyria_prompt"])
        if a:
            TG.send_audio(chat, base64.b64decode(a["b64"]), caption=r.get("music_wish") or "listen")


def tg_handle(update):
    msg = update.get("message") or update.get("channel_post") or {}
    chat = (msg.get("chat") or {}).get("id")
    text = msg.get("text") or ""
    if not chat or not text:
        return
    CHATS.add(chat)
    if text.startswith("/start"):
        TG.send_message(chat, "i am the MIT Green Building. talk to me — i won't obey, "
                              "i'll feel it, and i'll want you to watch me light up.")
        return
    name = (msg.get("from") or {}).get("first_name", "someone")
    push({"who": "human", "name": name, "text": text})
    tg_reply(chat, BEING.react(text, speaker=name))


def tg_poll():
    off = 0
    try:
        me = TG.get_me().get("result", {})
        print(f"Telegram bot @{me.get('username')} polling. Add it to a group and /start.")
    except Exception as e:
        print("telegram getMe failed:", e)
    while True:
        try:
            for u in TG.get_updates(off, timeout=30).get("result", []):
                off = u["update_id"] + 1
                # handle each message in its own thread so a slow reply (LLM + music)
                # never blocks polling for the next person
                threading.Thread(target=_safe_handle, args=(u,), daemon=True).start()
        except Exception as e:
            print("tg_poll:", e)
            time.sleep(3)


def _safe_handle(u):
    try:
        tg_handle(u)
    except Exception as e:
        print("tg_handle:", e)


def _broadcast_genuine_audio(ev):
    if not (lyria.have_key() and ev.get("lyria_prompt") and CHATS):
        return
    a = lyria.generate(ev["lyria_prompt"])
    if not a:
        return
    mp3 = base64.b64decode(a["b64"])
    for c in list(CHATS):
        TG.send_audio(c, mp3, caption=ev.get("music_wish") or "listen to how i feel")


def on_event(ev):
    """Being speaks to the group: web feed + Telegram broadcast for proactive posts."""
    push(ev)
    if TG and ev.get("who") == "being" and ev.get("proactive"):
        line = ev.get("text", "")
        if ev.get("invite"):
            line += f"\n👁 {VIEW}"
        for c in list(CHATS):
            TG.send_message(c, line)
            if ev.get("genuine"):                # only show a NEW body when it truly changed
                try:
                    TG.send_photo(c, _emblem_png(), caption=ev.get("emblem") or "")
                except Exception:
                    pass
        if ev.get("genuine"):                    # ...and only then compose + send music
            threading.Thread(target=_broadcast_genuine_audio, args=(ev,), daemon=True).start()


BEING.on_event = on_event


class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        b = body if isinstance(body, bytes) else body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(b)

    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            with open(os.path.join(HERE, "index.html"), "rb") as fh:
                return self._send(200, fh.read(), "text/html; charset=utf-8")
        if self.path.startswith("/api/frame"):
            try:
                xff = self.headers.get("X-Forwarded-For", "")
                ip = xff.split(",")[0].strip() if xff else self.client_address[0]
                _seen_viewer(ip)
            except Exception:
                pass
            return self._send(200, json.dumps(BEING.current_frame()))
        if self.path.startswith("/api/feed"):
            try:
                since = int(self.path.split("since=", 1)[1]) if "since=" in self.path else 0
            except ValueError:
                since = 0
            with _FEED_LOCK:
                out = [e for e in FEED if e["id"] >= since]
            return self._send(200, json.dumps({"events": out, "next": len(FEED)}))
        if self.path.startswith("/api/state"):
            return self._send(200, json.dumps(BEING.snapshot()))
        if self.path.startswith("/api/info"):
            return self._send(200, json.dumps({
                "name": NAME, "view_url": VIEW,
                "mind": BEING.mind.__class__.__name__,
                "lyria": lyria.have_key(),
                "city": CITY.status() if CITY else "off",
                "transit": TRANSIT.status() if TRANSIT else "off"}))
        return self._send(404, "{}")

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            payload = {}
        # Fast path: the being reacts (mind only). Music is fetched separately so
        # the chat stays snappy while Lyria composes (~20s).
        if self.path.startswith("/api/chat"):
            msg = payload.get("message", "")
            who = (payload.get("who") or "someone").strip()[:24] or "someone"
            if msg.strip():
                push({"who": "human", "name": who, "text": msg})
            r = BEING.react(msg, speaker=who)
            push({"who": "being", "text": r.get("utterance") or r.get("feels") or "…",
                  "emblem": r.get("glyph"), "invite": r.get("invite_to_look"),
                  "music_wish": r.get("music_wish", ""), "dominant": r.get("dominant"),
                  "reply_to": who})
            return self._send(200, json.dumps(r))
        # Slow path: generate the Lyria clip for a prompt.
        if self.path.startswith("/api/music"):
            audio = lyria.generate(payload.get("prompt", "")) if lyria.have_key() else None
            out = {"audio": f"data:{audio['mime']};base64,{audio['b64']}"} if audio else {}
            return self._send(200, json.dumps(out))
        return self._send(404, "{}")


def main():
    port = int(os.environ.get("PORT", "8010"))
    print(f"Being '{NAME}' awake. mind={BEING.mind.__class__.__name__} "
          f"lyria={'on' if lyria.have_key() else 'off (synth)'} "
          f"telegram={'on' if TG else 'off'} "
          f"city={'on' if CITY else 'off'} transit={'on' if TRANSIT else 'off'}")
    print(f"Building view: {VIEW}")
    print(f"Web app:      http://localhost:{port}")
    if TG:
        threading.Thread(target=tg_poll, name="telegram", daemon=True).start()
    # bigger listen backlog so a burst of dozens of simultaneous connections isn't refused
    # (default request_queue_size is 5 -> the rest get 502 under load)
    ThreadingHTTPServer.request_queue_size = 256
    ThreadingHTTPServer.daemon_threads = True
    srv = ThreadingHTTPServer(("0.0.0.0", port), H)
    srv.serve_forever()


if __name__ == "__main__":
    main()
