# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the App

No build step. Open `index.html` directly in a browser:

```bash
open index.html                      # macOS
python3 -m http.server 8080          # serve locally if needed for fetch/CORS
```

## Architecture

Everything lives in a single file: `index.html`. The entire application is written as JSX inside a `<script type="text/babel" data-type="module">` block — Babel standalone transpiles it in-browser at runtime.

**CDN dependencies (loaded in order):**
- Tailwind CSS Play CDN — configured inline via `tailwind.config` in a preceding `<script>` block
- React 18 UMD + ReactDOM 18 UMD — globals `React` and `ReactDOM`
- Babel Standalone — enables JSX and `data-type="module"` ESM imports in-browser
- `lucide-react` — imported via `https://esm.sh/lucide-react@latest` inside the Babel script

**Component tree:**
- `App` — owns all state; defined at the bottom of the script
- `DropZone` — reusable, instantiated twice (person / clothing); manages its own `isDragging` local state
- `OutputSection` — pure display component; renders one of four states based on props

**State flow in `App`:**
```
image1/image2        File objects for the two uploads
preview1/preview2    Object URLs for thumbnail display (from URL.createObjectURL)
isLoading            true while fetch is in-flight
resultImage          Object URL of the binary blob returned by the webhook
error                String shown in the error banner
```

Every `URL.createObjectURL()` call is paired with `URL.revokeObjectURL()` — on file replacement and in `handleReset`. This is critical to avoid memory leaks.

## API Integration

- **Endpoint:** `https://macawflyer.app.n8n.cloud/webhook/5c381939-3482-47fe-9d73-8706160652cd`
- **Method:** POST, `multipart/form-data` with fields `image1` and `image2`
- **Response:** binary image blob — handled with `await response.blob()` → `URL.createObjectURL(blob)`
- Never set `Content-Type` manually on FormData requests; the browser must set the multipart boundary automatically.
- A `TypeError` on fetch means a network/CORS failure (distinct from an HTTP error status).

## Styling Conventions

Tailwind utility classes only. The custom `shimmer-bg` CSS class (defined in `<style>`) is the only hand-written CSS — it animates the loading skeleton. The color palette is dark-first: `gray-950` page background, `gray-900` cards, `indigo-600` primary accent.
