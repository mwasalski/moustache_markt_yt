"""Orchestration: one World, one pass over the requested days."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterable
from datetime import date, timedelta
from pathlib import Path

from .config import SYSTEMS, SimulationConfig
from .crm import crm_files
from .ecom import LOOKBACK_DAYS, OrderCache, ecom_files
from .erp import erp_files
from .pos import pos_files
from .world import World
from .writers import OutputFile, write_file


def generate_day(world: World, day: date, version: str, systems: Iterable[str], cache: OrderCache) -> list[OutputFile]:
    systems = set(systems)
    files: list[OutputFile] = []
    if "erp" in systems:
        files += erp_files(world, day, version)
    if "crm" in systems:
        files += crm_files(world, day, version)
    if "ecom" in systems:
        files += ecom_files(world, day, version, cache)
    if "pos" in systems:
        files += pos_files(world, day, version)
    return files


def run(
    config: SimulationConfig,
    days: Iterable[date],
    output_root: Path,
    version: str = "v1",
    systems: Iterable[str] = SYSTEMS,
    write: Callable[[OutputFile, Path], int] = write_file,
    log: Callable[[str], None] | None = print,
) -> Counter:
    days = list(days)
    world = World(config)
    cache = OrderCache(world)
    stats: Counter = Counter()
    for position, day in enumerate(days, start=1):
        for file in generate_day(world, day, version, systems, cache):
            stats["bytes"] += write(file, output_root)
            stats["files"] += 1
            stats[f"rows {file.system}.{file.table}"] += len(file.rows)
        cache.evict_before(day - timedelta(days=LOOKBACK_DAYS + 1))
        if log and (position % 30 == 0 or position == len(days)):
            log(f"{day}  {position}/{len(days)} days  {stats['files']} files  {stats['bytes'] / 1e6:,.0f} MB")
    return stats
