# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the App

```bash
cp .env.example .env   # first time only — fill in WEBHOOK_URL
python3 server.py      # serves at http://localhost:8765
```

Always access via **http://localhost:8765**, never as a `file://` URL — the proxy `/generate` call will fail from `file://`.

## Architecture

Two files do all the work:

- `index.html` — entire React UI, JSX transpiled in-browser by Babel standalone via CDN. Sends `POST /generate` to the local proxy; never talks to n8n directly.
- `server.py` — stdlib-only Python proxy. Reads `.env`, serves static files via `SimpleHTTPRequestHandler`, and forwards `POST /generate` to the n8n webhook. The webhook URL is never sent to the browser.

**CDN dependencies in `index.html` (load order matters):**
Tailwind CSS Play CDN → React 18 UMD + ReactDOM 18 UMD → Babel Standalone. Icons are inline SVG components — no external icon CDN.

**Component tree:**
- `App` — owns all state
- `DropZone` — reusable, instantiated twice (person / clothing); manages its own `isDragging` local state
- `OutputSection` — pure display; renders one of four states (empty / loading / result / error)

**State in `App`:**
```
image1/image2        File objects for the two uploads
preview1/preview2    Object URLs for thumbnail display
isLoading            true while fetch is in-flight
resultImage          Object URL of the binary blob returned by /generate
error                String shown in the error banner
```

Every `URL.createObjectURL()` is paired with `URL.revokeObjectURL()` on replacement and in `handleReset` — skipping this causes memory leaks.

## API

- Client calls `POST /generate` (same-origin, no CORS needed)
- `server.py` forwards the raw multipart body to `WEBHOOK_URL` and streams the binary response back
- Never set `Content-Type` on FormData requests — the browser must set the multipart boundary
- Use `/webhook/…` URLs in n8n, not `/webhook-test/…` (test webhooks expire after one call)
- Server enforces 20 MB combined limit; client enforces 10 MB per image

## Secrets

- `WEBHOOK_URL` is in `.env` only (gitignored). `.env.example` is the committed template.
- The webhook URL must never appear in `index.html` or any committed file.

## Styling

Tailwind utility classes only. `shimmer-bg` (defined in `<style>`) is the only hand-written CSS — it animates the loading skeleton. Color palette: `gray-950` background, `gray-900` cards, `indigo-600` accent.
