#!/usr/bin/env python3
"""
Proxy server for Virtual Try-On.
Serves index.html and forwards POST /generate to the n8n webhook,
keeping the webhook URL out of browser-visible code.
Requires an active Supabase subscription before proxying.
"""

import base64
import http.server
import json as _json
import os
import sys
import urllib.request
import urllib.error

# ── Config ────────────────────────────────────────────────────────────────────

MAX_BODY_BYTES = 20 * 1024 * 1024  # 20 MB combined upload limit


def load_env(path=".env"):
    """Parse a .env file without external dependencies."""
    env = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                env[key.strip()] = val.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return env


_env = load_env()
WEBHOOK_URL       = _env.get("WEBHOOK_URL")                   or os.environ.get("WEBHOOK_URL", "")
PORT              = int(_env.get("PORT")                       or os.environ.get("PORT", 8765))
SUPABASE_URL      = _env.get("NEXT_PUBLIC_SUPABASE_URL")      or os.environ.get("NEXT_PUBLIC_SUPABASE_URL", "")
SUPABASE_ANON_KEY = _env.get("NEXT_PUBLIC_SUPABASE_ANON_KEY") or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY", "")

# ── Subscription check ────────────────────────────────────────────────────────


def _decode_jwt_sub(token):
    """Extract the 'sub' (user_id) from a JWT payload without signature verification."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        padding = 4 - len(parts[1]) % 4
        payload_b64 = parts[1] + ("=" * (padding % 4))
        decoded = base64.urlsafe_b64decode(payload_b64)
        return _json.loads(decoded).get("sub")
    except Exception:
        return None


def _has_active_subscription(token):
    """Return True if the JWT bearer has an active subscription in Supabase."""
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        return True  # not configured — skip check (dev mode)
    user_id = _decode_jwt_sub(token)
    if not user_id:
        return False
    url = (
        f"{SUPABASE_URL}/rest/v1/user_subscriptions"
        f"?user_id=eq.{user_id}&select=subscription_status"
    )
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("apikey", SUPABASE_ANON_KEY)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            rows = _json.loads(resp.read())
            status = rows[0].get("subscription_status", "") if rows else ""
            return status in ("active", "trialing")
    except Exception:
        return False


# ── Request handler ───────────────────────────────────────────────────────────


class Handler(http.server.SimpleHTTPRequestHandler):
    """Serve static files (GET) and proxy image generation (POST /generate)."""

    def do_POST(self):
        if self.path != "/generate":
            self.send_error(404, "Not found")
            return

        if not WEBHOOK_URL:
            self._json_error(500, "WEBHOOK_URL is not configured. Check your .env file.")
            return

        # ── Subscription gate ──────────────────────────────────────────────
        auth_header = self.headers.get("Authorization", "")
        token = auth_header.removeprefix("Bearer ").strip()
        if not token:
            self._json_error(403, "Authentication required.")
            return
        if not _has_active_subscription(token):
            self._json_error(403, "Active subscription required. Please subscribe at the app.")
            return

        # ── Content-type / size checks ─────────────────────────────────────
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            self._json_error(400, "Request must be multipart/form-data.")
            return

        try:
            content_length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            self._json_error(400, "Invalid Content-Length header.")
            return

        if content_length > MAX_BODY_BYTES:
            self._json_error(413, f"Upload too large. Maximum combined size is {MAX_BODY_BYTES // (1024*1024)} MB.")
            return

        body = self.rfile.read(content_length)

        try:
            req = urllib.request.Request(WEBHOOK_URL, data=body, method="POST")
            req.add_header("Content-Type", content_type)

            with urllib.request.urlopen(req, timeout=120) as resp:
                result = resp.read()
                result_ct = resp.headers.get("Content-Type", "application/octet-stream")

            self.send_response(200)
            self.send_header("Content-Type", result_ct)
            self.send_header("Content-Length", str(len(result)))
            self.end_headers()
            self.wfile.write(result)

        except urllib.error.HTTPError as e:
            upstream_body = e.read()
            self.send_response(e.code)
            self.send_header("Content-Type", e.headers.get("Content-Type", "application/json"))
            self.send_header("Content-Length", str(len(upstream_body)))
            self.end_headers()
            self.wfile.write(upstream_body)

        except urllib.error.URLError as e:
            self._json_error(502, f"Could not reach upstream server: {e.reason}")

        except TimeoutError:
            self._json_error(504, "Upstream request timed out.")

    def _json_error(self, code, message):
        body = f'{{"error": "{message}"}}'.encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        if self.path == "/generate":
            sys.stdout.write(f"[generate] {args[1]} {args[0].split()[0]}\n")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not WEBHOOK_URL:
        print("⚠  WEBHOOK_URL not set — copy .env.example to .env and fill it in.")
    else:
        print(f"✓  WEBHOOK_URL loaded")
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        print("⚠  NEXT_PUBLIC_SUPABASE_URL / NEXT_PUBLIC_SUPABASE_ANON_KEY not set — subscription check disabled.")
    else:
        print(f"✓  Supabase subscription gate active")

    print(f"→  Serving at http://localhost:{PORT}")

    with http.server.HTTPServer(("", PORT), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")
