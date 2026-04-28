# Virtual Try-On

Upload a photo of a person and a clothing item — or pick one from the built-in collection — and see the outfit virtually applied using AI.

## Requirements

- Python 3 (no packages needed — stdlib only)
- A modern browser (Chrome, Firefox, Safari)
- A Supabase project (auth + `user_subscriptions` table + Edge Functions)
- A Stripe account with a Payment Link and webhook
- An active n8n workflow with a webhook trigger

## Setup

```bash
# 1. Copy the environment template and fill in your values
cp .env.example .env

# 2. Start the server
python3 server.py
```

Then open **http://localhost:8765** in your browser.

> Do not open `index.html` directly from Finder. The app must be served through `server.py` or the `/generate` proxy call will fail.

## Configuration

Edit `.env`:

| Variable | Description |
|---|---|
| `WEBHOOK_URL` | Your n8n webhook URL (`/webhook/…`, not `/webhook-test/…`) |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase publishable anon key |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service-role key (used by Edge Functions only) |
| `STRIPE_SECRET_KEY` | Stripe secret key (used by Edge Functions only) |
| `PORT` | Port to serve on (default: `8765`) |

`.env` is gitignored and must never be committed.

## How it works

1. **Sign up / sign in** — Supabase Auth handles accounts
2. **Subscribe** — Stripe Payment Link charges $9.99/month; a webhook activates the account in Supabase
3. **Upload or pick clothing** — drag & drop a person photo, then upload a clothing image or click one from the built-in collection (Linen Shirt, Straw Fedora, Camo Wetsuit)
4. **Generate** — the server proxies both images to the n8n webhook and streams the result back
5. **Download** — hover the result image to reveal a save button

## Subscription lifecycle

- Stripe webhook → `activate-subscription` Edge Function → sets `subscription_status = 'active'` in `user_subscriptions`
- Cancellations set `subscription_status = 'canceled'`; the app reverts to the paywall on next load
- The `activate-subscription` Edge Function also accepts a Stripe Checkout `session_id` for immediate post-payment activation

## Limits

- Max 10 MB per image (client-side)
- Max 20 MB combined (server-side)
- Accepted formats: JPG, PNG, WEBP

## Project structure

```
index.html        React UI — all frontend code in one file (Babel in-browser)
server.py         Python proxy — keeps the webhook URL server-side
pics/             Built-in clothing images served as static files
api/              Supabase Edge Functions (activate-subscription, etc.)
.env              Secrets (gitignored — copy from .env.example)
.env.example      Template for .env
vercel.json       Vercel config for the /generate serverless proxy
```
