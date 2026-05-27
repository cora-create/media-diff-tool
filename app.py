import os
import json
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = int(os.environ.get("PORT", 8765))
API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
HTML_PATH = os.path.join(os.path.dirname(__file__), "index.html")


class Handler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        print(f"{self.address_string()} - {format % args}")

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            with open(HTML_PATH, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", len(content))
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        if self.path == "/api/claude":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)

            try:
                payload = json.loads(body)
                prompt_text = payload.get("prompt", "")
            except Exception:
                self.send_response(400)
                self.end_headers()
                return

            if not API_KEY:
                self._json_response(500, {"error": {"message": "ANTHROPIC_API_KEY environment variable is not set on the server."}})
                return

            request_body = json.dumps({
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 1000,
                "messages": [{"role": "user", "content": prompt_text}]
            }).encode("utf-8")

            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=request_body,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": API_KEY,
                    "anthropic-version": "2023-06-01",
                },
                method="POST"
            )

            try:
                with urllib.request.urlopen(req) as resp:
                    result = resp.read()
                self._json_response(200, json.loads(result))
            except urllib.error.HTTPError as e:
                error_body = json.loads(e.read())
                self._json_response(e.code, error_body)
            except Exception as e:
                self._json_response(500, {"error": {"message": str(e)}})
        else:
            self.send_response(404)
            self.end_headers()

    def _json_response(self, status, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    print(f"Starting server on port {PORT}")
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    server.serve_forever()
