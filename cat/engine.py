"""Transparent moving-average observation engine (clean-room).

Fast MA5 vs slow MA20 with a ±0.30% band. Outputs are observations for
display, not financial advice. Pure and deterministic: no I/O, no clock.
"""

import math
from collections import deque

FAST_WINDOW = 5
SLOW_WINDOW = 20
WARMUP_SAMPLES = 20
THRESHOLD = 0.0030  # ±0.30%
GAP_RESET_SECONDS = 90.0
ACTIVITY_GAIN = 30.0  # |spread| slope; dossier (CROW) parity per ruling #8.
ACTIVITY_IDLE = 0.12  # idle glow so the point cloud never goes fully dead.

SIGNAL_POSITIVE = "positive"
SIGNAL_NEGATIVE = "negative"
SIGNAL_NEUTRAL = "neutral"


def classify_spread(spread):
    """Map a fast-vs-slow spread to an observation. Exact ±band is neutral."""
    if spread > THRESHOLD:
        return SIGNAL_POSITIVE
    if spread < -THRESHOLD:
        return SIGNAL_NEGATIVE
    return SIGNAL_NEUTRAL


def activity_from_spread(spread):
    """Activity scalar in [0, 1]: idle glow plus |spread| gain, capped at 1.0."""
    return min(1.0, abs(spread) * ACTIVITY_GAIN + ACTIVITY_IDLE)


class ObservationEngine:
    """Rolling MA5/MA20 observer with warmup and gap reset."""

    def __init__(self):
        # Bounded: only the slow window is ever read, so the buffer never
        # grows past it no matter how long the process runs.
        self._samples = deque(maxlen=SLOW_WINDOW)  # (ts, price), oldest first
        self._last_ts = None
        self._total = 0  # accepted samples since construction/reset

    def reset(self):
        """Drop all buffered samples and restart warmup."""
        self._samples.clear()
        self._last_ts = None
        self._total = 0

    def status(self):
        """Warmup state for status displays."""
        count = len(self._samples)
        return {
            "sample_count": count,
            "needed": WARMUP_SAMPLES,
            "warming_up": count < WARMUP_SAMPLES,
        }

    def add_sample(self, price, ts):
        """Add one price; None while warming up, else an observation dict."""
        if not isinstance(price, (int, float)) or not math.isfinite(price):
            raise ValueError("price must be a finite number, got %r" % (price,))
        if price <= 0:
            raise ValueError("price must be positive, got %r" % (price,))
        if not isinstance(ts, (int, float)) or not math.isfinite(ts):
            raise ValueError("ts must be a finite number, got %r" % (ts,))

        if self._last_ts is not None and ts - self._last_ts > GAP_RESET_SECONDS:
            self.reset()
        self._samples.append((float(ts), float(price)))
        self._last_ts = float(ts)
        self._total += 1

        if len(self._samples) < WARMUP_SAMPLES:
            return None

        prices = [p for _, p in self._samples]
        ma_fast = sum(prices[-FAST_WINDOW:]) / FAST_WINDOW
        ma_slow = sum(prices[-SLOW_WINDOW:]) / SLOW_WINDOW
        spread = (ma_fast - ma_slow) / ma_slow
        return {
            "price": float(price),
            "ma_fast": ma_fast,
            "ma_slow": ma_slow,
            "spread": spread,
            "signal": classify_spread(spread),
            "activity": activity_from_spread(spread),
            "sample_count": self._total,
        }
