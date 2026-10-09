"""Textaris: a minimal private-notes inbox (unauthenticated V1)."""
import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from flask import Flask, jsonify, render_template_string, request

app = Flask(__name__)
DB_PATH = Path(os.environ.get("TEXTARIS_DB", Path(__file__).resolve().parent / "instance" / "messages.sqlite3"))
MAX_CHARS = 2000
# Basic per-IP abuse protection; resets on service restart.
recent = {}
recent_lock = Lock()

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Textaris</title>
<style>
:root { color-scheme: dark; }
* { box-sizing: border-box; }
body { margin: 0; min-height: 100vh; display: grid; place-items: center;
  background: #090e19; color: #e6eefc; font-family: system-ui, sans-serif; }
main { width: min(94vw, 620px); }
h1 { font-size: 1.2rem; font-weight: 500; color: #69d8ff; }
textarea { width: 100%; min-height: 140px; padding: 16px; resize: vertical;
  border: 1px solid #38516b; border-radius: 10px; background: #111c2e;
  color: inherit; font: 1rem/1.5 system-ui, sans-serif; outline: none; }
textarea:focus { border-color: #69d8ff; }
p { min-height: 1.5em; color: #95aabd; font-size: .85rem; }
</style>
</head>
<body>
<main>
<h1>Textaris</h1>
<form id="form">
<textarea id="message" maxlength="2000" autofocus placeholder="Write a note…" aria-label="Message"></textarea>
<p id="status" role="status">Enter to send · Shift+Enter for a new line</p>
</form>
</main>
<script>
const form = document.getElementById('form');
const field = document.getElementById('message');
const status = document.getElementById('status');
let busy = false;
field.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
    e.preventDefault();
    form.requestSubmit();
  }
});
form.addEventListener('submit', async e => {
  e.preventDefault();
  if (busy || !field.value.trim()) return;
  busy = true;
  const sent = field.value;
  status.textContent = 'Saving…';
  try {
    const response = await fetch('/api/messages', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({text: sent})
    });
    if (!response.ok) throw new Error('HTTP ' + response.status);
    // Preserve anything typed while the request was in flight.
    if (field.value === sent) field.value = '';
    status.textContent = 'Saved ✓';
  } catch (err) {
    status.textContent = 'Not saved — please try again (' + err.message + ')';
  } finally {
    busy = false;
    field.focus();
  }
});
</script>
</body>
</html>"""


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=10)
    db.execute("""CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL,
        text TEXT NOT NULL
    )""")
    db.commit()
    return db


@app.get("/")
def index():
    return render_template_string(PAGE)


@app.post("/api/messages")
def create_message():
    if not request.is_json:
        return jsonify(error="Expected JSON"), 415
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get("text"), str):
        return jsonify(error="Expected text"), 400
    message = data["text"].strip()
    if not message or len(message) > MAX_CHARS:
        return jsonify(error="Text must contain 1–2000 characters"), 400

    # No trust in X-Forwarded-For: this works with a single local Caddy proxy.
    ip = request.remote_addr or "unknown"
    now = time.monotonic()
    with recent_lock:
        # Cap memory use by pruning stale entries.
        if len(recent) > 1000:
            recent.clear()
        last = recent.get(ip, 0)
        if now - last < 2:
            return jsonify(error="Please wait a moment"), 429
        recent[ip] = now

    with connect() as db:
        db.execute("INSERT INTO messages (created_at, text) VALUES (?, ?)",
                   (datetime.now(timezone.utc).isoformat(timespec="seconds"), message))
        db.commit()
    return jsonify(ok=True), 201


if __name__ == "__main__":
    # Only bind locally. Put Caddy in front for HTTPS.
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5010")))
