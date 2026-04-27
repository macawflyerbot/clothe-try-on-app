from http.server import BaseHTTPRequestHandler
import os
import urllib.request
import urllib.error

MAX_BODY_BYTES = 20 * 1024 * 1024

WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")


class handler(BaseHTTPRequestHandler):

    def do_POST(self):
        if not WEBHOOK_URL:
            self._json_error(500, "WEBHOOK_URL is not configured.")
            return

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
            self._json_error(413, f"Upload too large. Maximum combined size is {MAX_BODY_BYTES // (1024 * 1024)} MB.")
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
            self._json_error(502, f"Could not reach upstream: {e.reason}")

        except TimeoutError:
            self._json_error(504, "Upstream request timed out.")

    def _json_error(self, code, message):
        body = f'{{"error": "{message}"}}'.encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
