"""Command line.

    python -m simulator backfill --start 2025-01-01 --end 2026-09-30 --output /Volumes/retail_sources/landing
    python -m simulator daily --date 2026-10-01 --output /Volumes/retail_sources/landing --schema-version v2
"""

from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path

from .config import DAILY_CHAOS_OVERRIDES, SCHEMA_VERSIONS, SYSTEMS, SimulationConfig
from .runner import run


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m simulator", description="Retail source-system simulator")
    modes = parser.add_subparsers(dest="mode", required=True)
    backfill = modes.add_parser("backfill", help="history for a date range (no type corruption by default)")
    backfill.add_argument("--start", type=date.fromisoformat, help="default: config.history_start")
    backfill.add_argument("--end", type=date.fromisoformat, required=True)
    daily = modes.add_parser("daily", help="one day, as the source systems would deliver it")
    daily.add_argument("--date", type=date.fromisoformat, required=True)
    for mode in (backfill, daily):
        mode.add_argument("--output", type=Path, required=True, help="local folder or /Volumes/<catalog>/<schema>")
        mode.add_argument("--schema-version", choices=SCHEMA_VERSIONS, default="v1")
        mode.add_argument("--systems", default=",".join(SYSTEMS), help="comma separated subset")
        mode.add_argument("--scale", type=float, default=1.0)
        mode.add_argument("--seed", type=int, default=42)
        mode.add_argument("--type-corruption-rate", type=float, help='share of numbers sent as text, e.g. "$ 123"')
        mode.add_argument("--parquet-type-drift-rate", type=float, help="share of ERP files with cost as text")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    chaos = dict(DAILY_CHAOS_OVERRIDES) if args.mode == "daily" else {}
    if args.type_corruption_rate is not None:
        chaos["type_corruption_rate"] = args.type_corruption_rate
    if args.parquet_type_drift_rate is not None:
        chaos["parquet_type_drift_rate"] = args.parquet_type_drift_rate
    config = SimulationConfig(seed=args.seed, scale=args.scale).with_chaos(**chaos)

    if args.mode == "backfill":
        start = args.start or config.history_start
        days = [start + timedelta(days=offset) for offset in range((args.end - start).days + 1)]
        if start > config.history_start:
            print(f"Note: CRM initial snapshot is only emitted on {config.history_start}.")
    else:
        days = [args.date]
    if not days:
        parser.error("empty date range")
    if days[0] < config.history_start or days[-1] > config.world_end:
        parser.error(f"dates must be within {config.history_start} .. {config.world_end}")
    systems = tuple(name.strip() for name in args.systems.split(",") if name.strip())
    unknown = sorted(set(systems) - set(SYSTEMS))
    if unknown:
        parser.error(f"unknown systems: {unknown}")

    stats = run(config, days, args.output, args.schema_version, systems)
    for key in sorted(k for k in stats if k.startswith("rows ")):
        print(f"{key[5:]:<22} {stats[key]:>12,}")
    print(f"{'files':<22} {stats['files']:>12,}\n{'MB':<22} {stats['bytes'] / 1e6:>12,.1f}")
    return 0
