"""KITTYBRAIN v0.1 local observation server (clean-room, stdlib only).

Polls a price source into the MA observation engine, journals results to
SQLite, and serves the last-80 as JSON. Binds 127.0.0.1 only.

Modes: showcase (deterministic synthetic series, labeled illustrative)
or live (read-only DEX Screener poll). Signals are observations,
not financial advice.
"""

import html
import json
import os
import sqlite3
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from cat import BRAND
from cat import engine as engine_mod
from cat import providers as providers_mod
from cat import showcase as showcase_mod

LOOPBACK_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
DEFAULT_POLL_SECONDS = 30
HISTORY_CAP = 80
EVENTS_CAP = 60
DB_FILENAME = "cat.sqlite3"
WEB_DIR = "web"
VERSION = "0.1"

WEB_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".json": "application/json",
}

LIVE_DISCLAIMER = "Live observations of public market data. Not financial advice."

STATE = {
    "engine": engine_mod.ObservationEngine(),
    "conn": None,
    "config": {},
    "latest": None,
    "last_error": None,
    "showcase_prices": [],
    "showcase_index": 0,
    "showcase_start_ts": 0.0,
    "events": [],
}


# --- config ---------------------------------------------------------------

def load_config(path="config.json"):
    """Load JSON config with safe defaults; missing file means defaults."""
    config = {
        "mode": "showcase",
        "chain": "solana",
        "pair": "",
        "second_market": {"chain": "", "pair": ""},
        "poll_seconds": DEFAULT_POLL_SECONDS,
        "showcase_seed": 7,
        "showcase_step_seconds": 1,
        "port": DEFAULT_PORT,
    }
    try:
        with open(path, "r", encoding="utf-8") as handle:
            loaded = json.load(handle)
    except FileNotFoundError:
        return config
    if isinstance(loaded, dict):
        config.update(loaded)
    return config


def resolve_host(value):
    """Loopback by default; 0.0.0.0 only with KITTYBRAIN_PUBLIC=1 (hosted deploy)."""
    if value == "0.0.0.0" and os.environ.get("KITTYBRAIN_PUBLIC") == "1":
        return "0.0.0.0"
    if value != LOOPBACK_HOST:
        print(
            "warning: non-loopback host %r refused; using %s (local only)"
            % (value, LOOPBACK_HOST),
            file=sys.stderr,
        )
        return LOOPBACK_HOST
    return LOOPBACK_HOST


def is_live_mode(mode):
    """Single home for the live-vs-illustrative branch used everywhere."""
    return mode == "live"


def live_blocker(config):
    """Return a human-readable reason live mode cannot poll, or None."""
    if not is_live_mode(config.get("mode")):
        return None
    if not config.get("chain") or not config.get("pair"):
        return (
            "live mode needs a verified chain + pair in config.json; "
            "no synthetic fallback is used"
        )
    return None


# --- session events ---------------------------------------------------------

def log_event(state, stage, kind, message, ts=None):
    """Append one session event; ring-capped, consecutive duplicates skipped.

    Stages mirror the trace UI: observe → evaluate → inspect. Only real
    session happenings are logged here — never scripted filler.
    """
    events = state.setdefault("events", [])
    if events and events[-1]["stage"] == stage and events[-1]["message"] == message:
        return events[-1]
    event = {
        "ts": time.time() if ts is None else ts,
        "stage": stage,
        "kind": kind,
        "message": message,
    }
    events.append(event)
    del events[:-EVENTS_CAP]
    return event


def recent_events(state, limit):
    """Last `limit` events, chronological, capped at EVENTS_CAP."""
    try:
        count = int(limit)
    except (TypeError, ValueError):
        count = EVENTS_CAP
    count = max(0, min(EVENTS_CAP, count))
    return list(state.get("events", [])[-count:] if count else [])


# --- radar --------------------------------------------------------------------

def build_radar(config, latest, warmup):
    """One honest radar row for the single tracked market (v0.1).

    Fields the price adapter cannot supply stay null with a reason —
    the UI renders those as NO DATA, never as zeros.
    """
    mode = config.get("mode", "showcase")
    if is_live_mode(mode):
        label = "Live · %s" % (config.get("chain") or "unknown chain")
        pool = config.get("pair") or ""
    else:
        label = "SHOWCASE (synthetic)"
        pool = "seed=%s" % config.get("showcase_seed", 7)
    missing = "adapter reports price only in v0.1"
    if latest is None:
        if warmup.get("warming_up"):
            note = "warming up %d/%d" % (
                warmup.get("sample_count", 0), warmup.get("needed", 20)
            )
        else:
            note = "no observation yet"
        return [{
            "label": label,
            "pool": pool,
            "price": None,
            "change_1h_pct": None,
            "volume_24h_usd": None,
            "liquidity_usd": None,
            "unavailable_reason": missing,
            "signal": "waiting",
            "spread": None,
            "activity": None,
            "sample_count": warmup.get("sample_count", 0),
            "note": note,
        }]
    return [{
        "label": label,
        "pool": pool,
        "price": latest["price"],
        "change_1h_pct": None,
        "volume_24h_usd": None,
        "liquidity_usd": None,
        "unavailable_reason": missing,
        "signal": latest["signal"],
        "spread": latest["spread"],
        "activity": latest["activity"],
        "sample_count": latest["sample_count"],
        "note": "observation",
    }]


# --- web files ------------------------------------------------------------------

def read_web_file(name, web_dir=WEB_DIR):
    """Read one file from web/; None when missing, unmapped, or escaping.

    Rejects absolute paths, parent traversal, and unknown suffixes so a
    request path can never reach outside the web directory.
    """
    if not name or name.startswith(("/", "\\")) or "\\" in name:
        return None
    parts = [p for p in name.split("/") if p not in ("", ".")]
    if not parts or ".." in parts:
        return None
    if any(p.startswith(".") for p in parts):
        return None
    suffix = "." + parts[-1].rsplit(".", 1)[-1].lower() if "." in parts[-1] else ""
    content_type = WEB_CONTENT_TYPES.get(suffix)
    if content_type is None:
        return None
    base = os.path.abspath(web_dir)
    target = os.path.abspath(os.path.join(base, *parts))
    if target != base and not target.startswith(base + os.path.sep):
        return None
    try:
        with open(target, "rb") as handle:
            return content_type, handle.read()
    except OSError:
        return None


# --- journal ----------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    price REAL NOT NULL,
    ma_fast REAL NOT NULL,
    ma_slow REAL NOT NULL,
    spread REAL NOT NULL,
    signal TEXT NOT NULL,
    activity REAL NOT NULL,
    mode TEXT NOT NULL,
    source TEXT NOT NULL
)
"""


def init_db(path):
    """Open (creating) the SQLite journal. check_same_thread=False: the
    poll loop and request threads share it under a lock."""
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.execute(SCHEMA)
    conn.commit()
    return conn


def record_observation(conn, row):
    """Append one observation row to the journal."""
    conn.execute(
        "INSERT INTO observations "
        "(ts, price, ma_fast, ma_slow, spread, signal, activity, mode, source)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            row["ts"],
            row["price"],
            row["ma_fast"],
            row["ma_slow"],
            row["spread"],
            row["signal"],
            row["activity"],
            row["mode"],
            row["source"],
        ),
    )
    conn.commit()


def last_observations(conn, limit):
    """Return up to `limit` most recent rows, chronological, cap 80."""
    try:
        count = int(limit)
    except (TypeError, ValueError):
        count = HISTORY_CAP
    count = max(0, min(HISTORY_CAP, count))
    if count == 0:
        return []
    cursor = conn.execute(
        "SELECT ts, price, ma_fast, ma_slow, spread, signal, activity,"
        " mode, source FROM observations ORDER BY id DESC LIMIT ?",
        (count,),
    )
    rows = [
        {
            "ts": ts,
            "price": price,
            "ma_fast": ma_fast,
            "ma_slow": ma_slow,
            "spread": spread,
            "signal": signal,
            "activity": activity,
            "mode": mode,
            "source": source,
        }
        for ts, price, ma_fast, ma_slow, spread, signal, activity, mode, source in cursor.fetchall()
    ]
    rows.reverse()
    return rows


# --- polling ------------------------------------------------------------------

DB_LOCK = threading.Lock()


def poll_once(state):
    """Take one sample from the configured source. Returns the observation
    or None (warming up / blocked / error; see state['last_error'])."""
    config = state["config"]
    mode = config.get("mode", "showcase")
    blocker = live_blocker(config)
    if blocker is not None:
        state["last_error"] = blocker
        log_event(state, "observe", "blocked", blocker)
        return None
    try:
        if is_live_mode(mode):
            quote = providers_mod.fetch_pair_price(
                config["chain"], config["pair"]
            )
            price = quote["price_usd"]
            ts = time.time()
            source = "dexscreener:%s:%s" % (config["chain"], config["pair"])
        else:
            prices = state["showcase_prices"]
            if not prices:
                state["last_error"] = "showcase series is empty"
                return None
            tick = state["showcase_index"]
            price = prices[tick % len(prices)]
            state["showcase_index"] = tick + 1
            step = config.get("showcase_step_seconds", 1)
            ts = state["showcase_start_ts"] + tick * step
            source = "showcase:seed=%s" % config.get("showcase_seed", 7)
    except providers_mod.ProviderError as exc:
        state["last_error"] = str(exc)  # visible, never synthetic
        log_event(state, "observe", "error", str(exc))
        return None

    obs = state["engine"].add_sample(price, ts)
    state["last_error"] = None
    if obs is None:
        warmup = state["engine"].status()
        log_event(
            state, "evaluate", "warming",
            "warming up %d/%d" % (warmup["sample_count"], warmup["needed"]),
        )
        return None
    row = dict(obs)
    row["ts"] = ts
    row["mode"] = "live" if is_live_mode(mode) else "showcase"
    row["source"] = source
    with DB_LOCK:
        record_observation(state["conn"], row)
    state["latest"] = row
    log_event(
        state, "inspect", "observation",
        "signal=%s spread=%+.3f%% activity=%.2f"
        % (row["signal"], row["spread"] * 100.0, row["activity"]),
    )
    return row


def poll_loop(state, stop_event):
    """Background sampler until stop_event is set."""
    config = state["config"]
    mode = config.get("mode", "showcase")
    if is_live_mode(mode):
        interval = config.get("poll_seconds", DEFAULT_POLL_SECONDS)
    else:
        interval = config.get("showcase_step_seconds", 1)
    try:
        interval = max(1, int(interval))
    except (TypeError, ValueError):
        interval = 1
    while not stop_event.is_set():
        poll_once(state)
        stop_event.wait(interval)


# --- HTTP ---------------------------------------------------------------------

def build_envelope(mode, payload):
    """Wrap any payload with brand/mode/illustrative labeling."""
    illustrative = not is_live_mode(mode)
    return {
        "brand": BRAND,
        "version": VERSION,
        "mode": mode,
        "illustrative": illustrative,
        "disclaimer": showcase_mod.DISCLAIMER if illustrative else LIVE_DISCLAIMER,
        "data": payload,
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "%s/%s" % (BRAND, VERSION)

    def _send_json(self, obj, status=200):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, text, status=200):
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_bytes(self, body, content_type, status=200):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_web(self, name, mode):
        found = read_web_file(name)
        if found is None:
            if name in ("index.html", ""):
                self._send_html(render_index_fallback(mode))
            else:
                self._send_json(
                    build_envelope(mode, {"error": "not found"}), status=404
                )
            return
        content_type, body = found
        self._send_bytes(body, content_type)

    def do_GET(self):  # noqa: N802 (stdlib handler naming)
        parsed = urlparse(self.path)
        config = STATE["config"]
        mode = config.get("mode", "showcase")
        if parsed.path == "/api/latest":
            self._send_json(build_envelope(mode, {"latest": STATE["latest"]}))
        elif parsed.path == "/api/history":
            query = parse_qs(parsed.query)
            try:
                limit = int(query.get("limit", [HISTORY_CAP])[0])
            except (TypeError, ValueError):
                limit = HISTORY_CAP
            with DB_LOCK:
                rows = last_observations(STATE["conn"], limit)
            self._send_json(build_envelope(mode, {"observations": rows}))
        elif parsed.path == "/api/status":
            payload = {
                "warmup": STATE["engine"].status(),
                "last_error": STATE["last_error"],
                "live_blocker": live_blocker(config),
            }
            self._send_json(build_envelope(mode, payload))
        elif parsed.path == "/api/radar":
            rows = build_radar(config, STATE["latest"], STATE["engine"].status())
            self._send_json(build_envelope(mode, {"markets": rows}))
        elif parsed.path == "/api/events":
            query = parse_qs(parsed.query)
            try:
                limit = int(query.get("limit", [30])[0])
            except (TypeError, ValueError):
                limit = 30
            self._send_json(
                build_envelope(mode, {"events": recent_events(STATE, limit)})
            )
        elif parsed.path in ("/", "/index.html"):
            self._serve_web("index.html", mode)
        elif not parsed.path.startswith("/api/"):
            self._serve_web(parsed.path.lstrip("/"), mode)
        else:
            self._send_json(build_envelope(mode, {"error": "not found"}), status=404)

    def log_message(self, *args):
        pass  # quiet demo server; errors surface via /api/status


def render_index_fallback(mode):
    """Minimal status page, used only when web/index.html is missing."""
    illustrative = not is_live_mode(mode)
    banner = ""
    if illustrative:
        banner = "<p><strong>Illustrative showcase:</strong> synthetic demo data.</p>"
    latest = STATE["latest"]
    if latest is None:
        detail = "<p>Warming up: need %d samples.</p>" % engine_mod.WARMUP_SAMPLES
    else:
        detail = "<p>Signal: %s · activity %.2f · spread %.3f%%</p>" % (
            html.escape(str(latest["signal"])),
            latest["activity"],
            latest["spread"] * 100.0,
        )
    error = STATE["last_error"]
    err_html = "<p>Last error: %s</p>" % html.escape(error) if error else ""
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>%s</title></head>
<body><h1>%s</h1>
<p>Mode: %s · local only (127.0.0.1)</p>
%s%s%s
<p><small>Rule-based observations of price data, not financial advice.</small></p>
</body></html>""" % (
        html.escape(BRAND),
        html.escape(BRAND),
        html.escape(mode),
        banner,
        detail,
        err_html,
    )


def build_state(config, db_path=DB_FILENAME):
    """Assemble server state (also used to reset between runs)."""
    state = {
        "engine": engine_mod.ObservationEngine(),
        "conn": init_db(db_path),
        "config": config,
        "latest": None,
        "last_error": live_blocker(config),
        "showcase_prices": showcase_mod.generate_series(
            seed=config.get("showcase_seed", 7), n=240
        ),
        "showcase_index": 0,
        "showcase_start_ts": time.time(),
        "events": [],
    }
    log_event(
        state, "observe", "start",
        "server started in %s mode (local only)" % config.get("mode", "showcase"),
    )
    return state


def resolve_port(config):
    """PORT env (hosted deploy) wins; falls back to config file, then default."""
    try:
        return int(os.environ.get("PORT", config.get("port", DEFAULT_PORT)))
    except (TypeError, ValueError):
        return config.get("port", DEFAULT_PORT)


def main(argv=None):
    config = load_config()
    host = resolve_host(config.get("host", LOOPBACK_HOST))
    port = resolve_port(config)
    STATE.update(build_state(config))
    stop_event = threading.Event()
    worker = threading.Thread(
        target=poll_loop, args=(STATE, stop_event), daemon=True
    )
    worker.start()
    server = ThreadingHTTPServer((host, port), Handler)
    scope = "local only" if host == LOOPBACK_HOST else "public bind (hosted)"
    print("%s v%s on http://%s:%d (%s mode, %s)"
          % (BRAND, VERSION, host, port, config.get("mode", "showcase"), scope))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        server.server_close()


if __name__ == "__main__":
    main()
