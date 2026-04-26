# Virtual Try-On

Upload a photo of a person and a clothing item, and see the outfit virtually applied using AI.

## Requirements

- Python 3 (no packages needed — stdlib only)
- A modern browser (Chrome, Firefox, Safari)
- An active n8n workflow with a webhook trigger

## Setup

```bash
# 1. Copy the environment template and fill in your webhook URL
cp .env.example .env

# 2. Start the server
python3 server.py
```

Then open **http://localhost:8765** in your browser.

> Do not open `index.html` directly from Finder. The app must be served through `server.py` or the API calls will be blocked by the browser.

## Configuration

Edit `.env`:

| Variable | Description |
|---|---|
| `WEBHOOK_URL` | Your n8n webhook URL (`/webhook/…`, not `/webhook-test/…`) |
| `PORT` | Port to serve on (default: `8765`) |

`.env` is gitignored and must never be committed.

## How it works

1. Upload a **person photo** and a **clothing image** using the drag-and-drop zones
2. Click **Generate Try-On**
3. The result image appears in the output section — hover to reveal a download button

## Limits

- Max 10 MB per image (client-side check)
- Max 20 MB combined (server-side check)
- Accepted formats: JPG, PNG, WEBP

## Project structure

```
index.html      React UI — all frontend code in one file
server.py       Python proxy server — keeps the webhook URL out of the browser
.env            Secrets (gitignored — copy from .env.example)
.env.example    Template for .env
```
