"""Deterministic showcase series (clean-room).

Seeded synthetic prices for offline demos. Every consumer must label
this output illustrative; it is not market data.
"""

import random

MODE = "showcase"
ILLUSTRATIVE = True
DISCLAIMER = (
    "Illustrative showcase: synthetic data for demo only. "
    "Observations are not financial advice."
)


def generate_series(seed=7, n=120, start=100.0):
    """Return n positive prices; identical inputs give identical outputs
    within a Python version (random-module seeding is version-specific)."""
    rng = random.Random(seed)
    price = float(start)
    series = [price]
    for _ in range(max(0, n - 1)):
        drift = rng.uniform(-0.008, 0.008)
        wave = 0.004 * rng.uniform(-1.0, 1.0)
        price = max(0.01, price * (1.0 + drift + wave))
        series.append(price)
    return series
