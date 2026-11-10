"""Simulator tests: determinism and the CLI. A tiny scale keeps each run around a second."""

from __future__ import annotations

from datetime import date

import pytest

from simulator.cli import main
from simulator.config import SimulationConfig
from simulator.runner import run

DAYS = [date(2025, 1, 1), date(2025, 1, 2)]


def generate(seed: int) -> dict:
    """Runs the simulator in memory: relative path -> rows, nothing written to disk."""
    files = {}

    def collect(file, root):
        files[str(file.relative_path)] = file.rows
        return 0

    run(SimulationConfig(seed=seed, scale=0.05), DAYS, output_root=None, write=collect, log=None)
    return files


def test_same_seed_gives_identical_data():
    assert generate(seed=42) == generate(seed=42)


def test_different_seed_gives_different_data():
    assert generate(seed=42) != generate(seed=7)


def test_cli_backfill_writes_partitioned_files(tmp_path, capsys):
    exit_code = main(["backfill", "--start", "2025-01-01", "--end", "2025-01-02",
                      "--scale", "0.05", "--output", str(tmp_path)])
    assert exit_code == 0
    assert {path.name for path in tmp_path.iterdir()} == {"erp", "crm", "ecom", "pos"}
    assert list(tmp_path.glob("erp/*/load_date=2025-01-02/*"))


def test_cli_rejects_unknown_system(tmp_path):
    with pytest.raises(SystemExit):
        main(["daily", "--date", "2025-01-01", "--systems", "erp,sap", "--output", str(tmp_path)])
