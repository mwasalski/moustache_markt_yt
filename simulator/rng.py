"""Deterministic randomness: every stream is keyed, so results never depend on call order."""

from __future__ import annotations

import math
import random
import uuid
from bisect import bisect_right
from collections.abc import Sequence
from itertools import accumulate
from typing import Generic, TypeVar

T = TypeVar("T")


def make_rng(seed: int, *key: object) -> random.Random:
    """Same seed + key -> same numbers on any machine (str seeds are hashed with SHA-512)."""
    return random.Random("|".join(str(part) for part in (seed, *key)))


def poisson(rng: random.Random, lam: float) -> int:
    if lam <= 0:
        return 0
    if lam < 30:  # Knuth
        limit, count, product = math.exp(-lam), 0, 1.0
        while True:
            product *= rng.random()
            if product <= limit:
                return count
            count += 1
    return max(0, round(rng.gauss(lam, math.sqrt(lam))))


def pick_weighted(rng: random.Random, cum_weights: Sequence[float], upto: int | None = None) -> int:
    """Index drawn proportionally to weights, optionally restricted to the first `upto` items."""
    high = len(cum_weights) if upto is None else upto
    if high <= 0:
        raise ValueError("Nothing to pick from")
    target = rng.random() * cum_weights[high - 1]
    return min(bisect_right(cum_weights, target, 0, high), high - 1)


class Weighted(Generic[T]):
    """Reusable weighted choice: Weighted([("BLIK", 0.4), ("CARD", 0.6)])(rng)."""

    def __init__(self, options: Sequence[tuple[T, float]]) -> None:
        self.values = [value for value, _ in options]
        self.cum_weights = list(accumulate(weight for _, weight in options))

    def __call__(self, rng: random.Random) -> T:
        return self.values[pick_weighted(rng, self.cum_weights)]


def uuid_from(rng: random.Random) -> str:
    return str(uuid.UUID(int=rng.getrandbits(128), version=4))
