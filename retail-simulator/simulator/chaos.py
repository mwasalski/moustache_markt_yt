"""Chaos layer: delivery and formatting problems. Every decision is keyed, hence reproducible."""

from __future__ import annotations

import random
from collections.abc import Iterator
from decimal import Decimal

from .config import SimulationConfig
from .formats import us_amount
from .rng import make_rng

_CORRUPTED_AMOUNTS = ("$ {dot}", "${us}", "USD {dot}", "N/A", "", "{dot} ")


def corrupt_amount(value: Decimal, rng: random.Random) -> str:
    """A number that arrives as text: '$ 123.45', '$1,299.99', 'N/A', ''..."""
    return rng.choice(_CORRUPTED_AMOUNTS).format(dot=f"{value:.2f}", us=us_amount(value))


def lateness(config: SimulationConfig, system: str, key: str) -> int:
    """0 for on-time delivery, otherwise 1-2 (days or export runs) late."""
    rate = config.chaos.late_arrival_rate
    if rate <= 0:
        return 0
    rng = make_rng(config.seed, "chaos-late", system, key)
    if rng.random() >= rate:
        return 0
    return 1 if rng.random() < 0.7 else 2


def with_duplicates(records: list, rate: float, rng: random.Random) -> list:
    if rate <= 0:
        return records
    result = []
    for record in records:
        result.append(record)
        if rng.random() < rate:
            result.append(record)
    return result


def corrupt_numbers(record: dict, paths: tuple[tuple[str, ...], ...], rate: float, rng: random.Random) -> None:
    """Replaces Decimal values at the given paths ('*' = every list element) with corrupted text."""
    for path in paths:
        for container, key in _locate(record, path):
            value = container[key]
            if isinstance(value, Decimal) and rng.random() < rate:
                container[key] = corrupt_amount(value, rng)


def _locate(node: object, path: tuple[str, ...]) -> Iterator[tuple[dict, str]]:
    if not path:
        return
    head, rest = path[0], path[1:]
    if head == "*":
        if isinstance(node, list):
            for item in node:
                yield from _locate(item, rest)
        return
    if not isinstance(node, dict) or head not in node:
        return
    if rest:
        yield from _locate(node[head], rest)
    else:
        yield node, head
