"""
data_server.py
--------------
Lightweight HTTP data server that serves large DataFrames to the AG Grid
component in chunks, enabling AG Grid's Infinite Row Model.

Runs as a background daemon thread.  The React component fetches rows in
blocks (500 at a time by default) as the user scrolls, so the full dataset
is never serialized or sent to the browser at once.

ENDPOINTS
---------
GET /meta?key=K
    {"totalRows": N, "columns": ["col1", ...]}

GET /rows?key=K&start=0&end=499
    JSON array of N row-dicts for the inclusive range [start, end].

CORS
----
All responses include Access-Control-Allow-Origin: * so the Streamlit
component iframe (on port 8501) can fetch from this server's port.
"""

import http.server
import json
import socket
import threading
from urllib.parse import urlparse, parse_qs

import pandas as pd


class _DataStore:
    """Thread-safe store for DataFrames keyed by an arbitrary string."""

    def __init__(self):
        self._frames: dict = {}
        self._lock = threading.RLock()

    def store(self, key: str, df: "pd.DataFrame") -> None:
        with self._lock:
            self._frames[key] = df

    def get_meta(self, key: str) -> dict | None:
        with self._lock:
            df = self._frames.get(key)
            if df is None:
                return None
            return {"totalRows": len(df), "columns": list(df.columns)}

    def get_rows_json(self, key: str, start: int, end: int) -> str | None:
        with self._lock:
            df = self._frames.get(key)
            if df is None:
                return None
            # pandas to_json handles NaN→null and numpy types natively
            return df.iloc[start : end + 1].to_json(orient="records")

    def clear(self, key: str) -> None:
        with self._lock:
            self._frames.pop(key, None)


_store = _DataStore()


class _Handler(http.server.BaseHTTPRequestHandler):
    """Minimal HTTP request handler for /meta and /rows."""

    def log_message(self, *args):
        pass  # suppress access logs

    def do_OPTIONS(self):
        self._send(200, b"", "text/plain")

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        key = params.get("key", [""])[0]

        if parsed.path == "/meta":
            meta = _store.get_meta(key)
            if meta is None:
                self._send(404, b'{"error":"not found"}', "application/json")
            else:
                self._send(200, json.dumps(meta).encode(), "application/json")

        elif parsed.path == "/rows":
            start = int(params.get("start", ["0"])[0])
            end = int(params.get("end", ["99"])[0])
            body = _store.get_rows_json(key, start, end)
            if body is None:
                self._send(404, b'{"error":"not found"}', "application/json")
            else:
                self._send(200, body.encode(), "application/json")

        else:
            self._send(404, b'{"error":"not found"}', "application/json")

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.end_headers()
        self.wfile.write(body)


_server_port: int | None = None
_server_lock = threading.Lock()


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def get_or_start_server() -> int:
    """
    Start the data server daemon thread if not already running.
    Returns the port number.  Thread-safe.
    """
    global _server_port
    with _server_lock:
        if _server_port is not None:
            return _server_port
        port = _find_free_port()
        httpd = http.server.HTTPServer(("127.0.0.1", port), _Handler)
        t = threading.Thread(
            target=httpd.serve_forever,
            daemon=True,
            name="PSDataServer",
        )
        t.start()
        _server_port = port
        return port


def server_url() -> str:
    """Return the base URL of the data server, starting it if necessary."""
    return f"http://127.0.0.1:{get_or_start_server()}"


def store_dataframe(key: str, df: "pd.DataFrame") -> None:
    """Register a DataFrame for serving under the given key."""
    _store.store(key, df)


def clear_dataframe(key: str) -> None:
    """Remove a DataFrame from the store."""
    _store.clear(key)
