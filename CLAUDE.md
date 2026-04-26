# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the App

```bash
cp .env.example .env   # first time only — fill in WEBHOOK_URL
python3 server.py      # serves at http://localhost:8765
```

Open **http://localhost:8765** in the browser. Do not open `index.html` directly as a `file://` URL — the proxy fetch to `/generate` will fail.

## Architecture

**Two files do all the work:**

- `index.html` — entire React UI (JSX transpiled in-browser by Babel standalone via CDN). Sends `POST /generate` to the local proxy; never talks to n8n directly.
- `server.py` — stdlib-only Python proxy. Reads `.env`, serves static files (via `SimpleHTTPRequestHandler`), and forwards `POST /generate` to the n8n webhook. The webhook URL is never sent to the browser.

**CDN dependencies in `index.html` (loaded in order):**
- Tailwind CSS Play CDN — configured inline via `tailwind.config`
- React 18 UMD + ReactDOM 18 UMD — globals `React` and `ReactDOM`
- Babel Standalone — enables JSX in `<script type="text/babel">`
- Icons are inline SVG components (no external icon CDN)

**Component tree in `index.html`:**
- `App` — owns all state
- `DropZone` — reusable, instantiated twice (person / clothing); manages its own `isDragging` local state
- `OutputSection` — pure display; renders one of four states based on props

**State flow in `App`:**
```
image1/image2        File objects for the two uploads
preview1/preview2    Object URLs for thumbnail display (from URL.createObjectURL)
isLoading            true while fetch is in-flight
resultImage          Object URL of the binary blob returned by /generate
error                String shown in the error banner
```

Every `URL.createObjectURL()` call is paired with `URL.revokeObjectURL()` — on file replacement and in `handleReset`. This is critical to avoid memory leaks.

## API Integration

- **Client calls:** `POST /generate` (same-origin, no CORS)
- **Proxy forwards to:** `WEBHOOK_URL` from `.env`
- **Request:** `multipart/form-data` with fields `image1` and `image2`
- **Response:** binary image blob streamed back through the proxy
- Never set `Content-Type` manually on FormData requests; the browser sets the multipart boundary automatically.
- Server enforces a 20 MB combined upload limit; client enforces 10 MB per image.

## Secrets & Security

- `WEBHOOK_URL` lives only in `.env` (gitignored). Copy `.env.example` to get started.
- The n8n webhook URL is never sent to the browser — the proxy is the only process that knows it.
- `.env` must never be committed. `.env.example` (no real values) is committed instead.

## Styling Conventions

Tailwind utility classes only. The custom `shimmer-bg` CSS class (defined in `<style>`) is the only hand-written CSS — it animates the loading skeleton. The color palette is dark-first: `gray-950` page background, `gray-900` cards, `indigo-600` primary accent.
