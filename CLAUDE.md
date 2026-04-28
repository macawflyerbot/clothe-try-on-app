# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the App

```bash
cp .env.example .env   # first time only — fill in all variables
python3 server.py      # serves at http://localhost:8765
```

Always access via **http://localhost:8765**, never as a `file://` URL — the proxy `/generate` call will fail from `file://`.

## Architecture

Two files do most of the work:

- `index.html` — entire React UI, JSX transpiled in-browser by Babel standalone via CDN. Sends `POST /generate` to the local proxy; never talks to n8n directly.
- `server.py` — stdlib-only Python proxy. Reads `.env`, serves static files (including `pics/`) via `SimpleHTTPRequestHandler`, and forwards `POST /generate` to the n8n webhook. The webhook URL is never sent to the browser.

**CDN dependencies in `index.html` (load order matters):**
Tailwind CSS Play CDN → React 18 UMD + ReactDOM 18 UMD → Babel Standalone → Supabase JS. Icons are inline SVG components — no external icon CDN.

**Component tree:**
- `App` — owns all state; renders one of: loading spinner, `AuthForm`, `PaymentWall`, or the main try-on UI
- `AuthForm` — sign-up / sign-in form backed by Supabase Auth
- `PaymentWall` — shows Stripe Payment Link; polls or calls `activate-subscription` Edge Function on return
- `DropZone` — reusable, instantiated twice (person / clothing); manages its own `isDragging` local state
- `OutputSection` — pure display; renders one of four states (empty / loading / result / error)

**State in `App`:**
```
session              Supabase Auth session (null = not logged in)
subscriptionStatus   null | 'active' | 'inactive'
image1/image2        File objects for the two uploads
preview1/preview2    Object URLs for thumbnail display
selectedPreset       ID of the active preset clothing item (null if custom upload)
isLoading            true while fetch is in-flight
resultImage          Object URL of the binary blob returned by /generate
error                String shown in the error banner
```

Every `URL.createObjectURL()` is paired with `URL.revokeObjectURL()` on replacement and in `handleReset` — skipping this causes memory leaks.

## Auth & Subscription Flow

- Supabase Auth handles sign-up / sign-in (email + password).
- After login, `App` checks `user_subscriptions` table for `subscription_status = 'active' | 'trialing'`.
- If inactive → `PaymentWall` renders a Stripe Payment Link with `client_reference_id` set to the Supabase user ID.
- On return from Stripe, the app either calls `activate-subscription` Edge Function (with `session_id`) or polls the table directly.
- Stripe webhooks (`checkout.session.completed`, `customer.subscription.*`) also update the table server-side via Edge Functions.

## Clothing Gallery (Preset Items)

`PRESET_CLOTHES` (constant in `index.html`) lists items served from `pics/`:

```js
{ id: 'shirt',   file: '29855415_58972031_600.jpg',                             name: 'Linen Shirt'  }
{ id: 'fedora',  file: 'before_dark_packable_unisex_fedora_-_naturalblack.jpg', name: 'Straw Fedora' }
{ id: 'wetsuit', file: 'wetsuit.jpg',                                           name: 'Camo Wetsuit' }
```

`handlePresetSelect` fetches the image from `/pics/<file>`, wraps it in a `File` object, and calls `handleFile2` — identical to a manual upload from that point on. The gallery shows below the clothing DropZone; selecting a preset highlights it with an indigo ring. Uploading manually or resetting clears the selection.

To add more presets: drop images into `pics/` and add an entry to `PRESET_CLOTHES`.

## API

- Client calls `POST /generate` (same-origin, no CORS needed) with `Authorization: Bearer <supabase_access_token>`
- `server.py` forwards the raw multipart body to `WEBHOOK_URL` and streams the binary response back
- Never set `Content-Type` on FormData requests — the browser must set the multipart boundary
- Use `/webhook/…` URLs in n8n, not `/webhook-test/…` (test webhooks expire after one call)
- Server enforces 20 MB combined limit; client enforces 10 MB per image

## Secrets

- All secrets live in `.env` only (gitignored). `.env.example` is the committed template.
- Required: `WEBHOOK_URL`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `STRIPE_SECRET_KEY`
- None of these must ever appear in `index.html` or any committed file.

## Styling

Tailwind utility classes only. `shimmer-bg` (defined in `<style>`) is the only hand-written CSS — it animates the loading skeleton. Color palette: `gray-950` background, `gray-900` cards, `indigo-600` accent.
