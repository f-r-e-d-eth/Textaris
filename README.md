# Textaris

A tiny write-only inbox for quick notes. Type a message and press **Enter** to save; use **Shift+Enter** for a newline.

## Quick start (Linux)

```bash
git clone https://github.com/f-r-e-d-eth/Textaris.git
cd Textaris
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py
```

Open http://127.0.0.1:5010 locally. For public access, place the app behind Caddy and proxy to `127.0.0.1:5010`.

Messages are stored as UTC ISO timestamps in `instance/messages.sqlite3`, which is ignored by Git. Override the location with `TEXTARIS_DB=/path/to/messages.sqlite3`.

Example Caddy route (add inside your existing site block, before a catch-all handler):

```caddyfile
handle /text* {
    reverse_proxy 127.0.0.1:5010
}
```

**Important:** This example route works when Textaris is mounted at the root of a dedicated host, but not reliably at a `/text` prefix: the app uses root-relative API URLs. Prefer a dedicated host like `text.f-r-e-d.eu`, or use a rewrite/proxy scheme that also handles `/api/messages`. Keep your existing Portaris `text` command as a link to that host.

## V1 limitations

- **No authentication:** anybody who finds the public URL can submit notes. Do not enter sensitive information.
- **No download endpoint:** contents cannot be retrieved from the public website. For now use SSH on the server, or query SQLite locally.
- **Basic in-memory rate limiting:** not a defense against determined abuse or multiple proxy workers.
- Back up the database separately; Git does not contain messages.

## Inspect saved notes on the server

```bash
sqlite3 instance/messages.sqlite3 'SELECT id, created_at, text FROM messages ORDER BY id DESC LIMIT 20;'
```

A future separate synchronizer can import records into Memaris without either repository depending on the other.
