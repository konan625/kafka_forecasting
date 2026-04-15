from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer


class MockUFSHandler(BaseHTTPRequestHandler):
    def _send_json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802 (HTTP method signature)
        if self.path != "/forecast":
            self._send_json(404, {"error": "not_found"})
            return

        content_len = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(content_len) if content_len > 0 else b"{}"
        payload = json.loads(raw.decode())

        # Very small deterministic response so bridge behavior is easy to verify.
        response = {
            "model": "mock-ufs",
            "status": "ok",
            "received_identity": {
                "job_id": payload.get("job_id"),
                "node_ip": payload.get("node_ip"),
                "object_name": payload.get("object_name"),
                "kpi_name": payload.get("kpi_name"),
            },
            "forecast_points": [
                {"ds": 1750000000000, "Forecast": 10.5},
                {"ds": 1750003600000, "Forecast": 11.1},
                {"ds": 1750007200000, "Forecast": 10.9},
            ],
        }
        self._send_json(200, response)


def main() -> None:
    server = HTTPServer(("0.0.0.0", 8080), MockUFSHandler)
    print("[MOCK-UFS] Listening on http://localhost:8080/forecast")
    server.serve_forever()


if __name__ == "__main__":
    main()
