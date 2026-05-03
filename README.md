# Virtual Try-On

Upload a photo of a person and a clothing item — or pick one from the built-in collection — and see the outfit virtually applied using AI.

## Requirements

- Python 3 (no packages needed — stdlib only)
- A modern browser (Chrome, Firefox, Safari)
- A Supabase project with the `user_subscriptions` table (see [Supabase setup](#supabase-setup))
- A Stripe account with a Payment Link and webhook (see [Stripe setup](#stripe-setup))
- An active n8n workflow with a webhook trigger (see [n8n workflow](#n8n-workflow))

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
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL (e.g. `https://abcdef.supabase.co`) |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase publishable anon key (safe to expose in the browser) |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service-role key — used by Edge Functions only, never sent to the browser |
| `STRIPE_SECRET_KEY` | Stripe secret key (`sk_live_…` or `sk_test_…`) — used by Edge Functions only |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret (`whsec_…`) — used to verify webhook payloads |
| `NEXT_PUBLIC_STRIPE_PAYMENT_LINK_URL` | Full URL of your Stripe Payment Link (e.g. `https://buy.stripe.com/…`) |
| `PORT` | Port to serve on (default: `8765`) |

`.env` is gitignored and must never be committed.

## Supabase setup

### Auth

Enable **Email** provider under **Authentication → Providers**. No extra config is needed.

### `user_subscriptions` table

Run this SQL in the Supabase SQL editor:

```sql
create table public.user_subscriptions (
  id                   uuid primary key default gen_random_uuid(),
  user_id              uuid not null references auth.users(id) on delete cascade,
  stripe_customer_id   text,
  stripe_subscription_id text,
  subscription_status  text not null default 'inactive',
  updated_at           timestamptz not null default now(),
  unique (user_id)
);

-- Allow users to read their own row; Edge Functions use the service-role key to write.
alter table public.user_subscriptions enable row level security;

create policy "Users can read their own subscription"
  on public.user_subscriptions for select
  using (auth.uid() = user_id);
```

### Edge Functions

Deploy the `activate-subscription` function from the `supabase/functions/` directory (if present) using the Supabase CLI:

```bash
supabase functions deploy activate-subscription
```

The function accepts either:
- A Stripe webhook event payload (called automatically by Stripe), or
- A `{ session_id }` JSON body (called by the client immediately after Stripe Checkout returns)

It writes `subscription_status = 'active'` (or `'canceled'`) to `user_subscriptions`.

## Stripe setup

1. Create a **Product** (e.g. "Virtual Try-On") and a recurring **Price** of $9.99/month.
2. Create a **Payment Link** for that price. Set `client_reference_id` to `{client_reference_id}` — the app passes the Supabase user ID here so the webhook can match the Stripe customer to the right user.
3. Create a **Webhook** endpoint pointing at your Edge Function URL (`https://<project-ref>.supabase.co/functions/v1/activate-subscription`). Subscribe to these events:
   - `checkout.session.completed`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
4. Copy the **Signing secret** (`whsec_…`) into `STRIPE_WEBHOOK_SECRET` in `.env`.

## n8n workflow

The n8n webhook receives a `multipart/form-data` POST with two fields:

| Field | Type | Description |
|---|---|---|
| `person` | binary (image) | Photo of the person |
| `clothing` | binary (image) | Photo of the clothing item |

The workflow should pass both images to a virtual try-on AI node (e.g. Replicate, Fashn.ai, or a custom model), then respond with the resulting image as a binary body. The `Content-Type` header of the response (`image/jpeg`, `image/png`, etc.) is forwarded as-is to the browser.

Use a `/webhook/…` URL — `/webhook-test/…` URLs expire after a single call.

## How it works

1. **Sign up / sign in** — Supabase Auth handles accounts (email + password)
2. **Subscribe** — Stripe Payment Link charges $9.99/month; the webhook activates the account in Supabase
3. **Upload or pick clothing** — drag & drop a person photo, then upload a clothing image or click one from the built-in collection (Linen Shirt, Straw Fedora, Camo Wetsuit)
4. **Generate** — the server proxies both images to the n8n webhook and streams the result back
5. **Download** — hover the result image to reveal a save button

## Subscription lifecycle

- Stripe webhook → `activate-subscription` Edge Function → sets `subscription_status = 'active'` in `user_subscriptions`
- Cancellations set `subscription_status = 'canceled'`; the app reverts to the paywall on next load
- The `activate-subscription` Edge Function also accepts a Stripe Checkout `session_id` for immediate post-payment activation (no waiting for the webhook)

## Adding clothing presets

Drop images into `pics/` and add an entry to the `PRESET_CLOTHES` constant near the top of `index.html`:

```js
{ id: 'my-item', file: 'my-item.jpg', name: 'My Item' }
```

The preset gallery renders below the clothing drop zone; selecting a preset highlights it with an indigo ring. Uploading a file manually clears the selection.

## Limits

- Max 10 MB per image (client-side)
- Max 20 MB combined (server-side)
- Accepted formats: JPG, PNG, WEBP

## Project structure

```
index.html          React UI — all frontend code in one file (Babel in-browser transpilation)
server.py           Python stdlib proxy — keeps WEBHOOK_URL server-side, serves static files
api/generate.py     Vercel serverless equivalent of server.py — deployed automatically by vercel.json
pics/               Built-in clothing images served as static files
.env                Secrets (gitignored — copy from .env.example)
.env.example        Template listing all required environment variables
vercel.json         Routes /generate to api/generate.py when deployed on Vercel
```

## Deploying to Vercel

Push the repo to GitHub, then import it in the Vercel dashboard. Set all variables from `.env` as Vercel environment variables. The `vercel.json` already routes `POST /generate` to `api/generate.py`, so no extra config is needed.
