# Moustache Markt

A hands-on Databricks data platform built step by step, one notebook per episode.

The company is **Moustache Markt**, a fictional electronics retail chain in New England (US).
Its source systems (ERP, CRM, e-commerce, POS) are simulated by a deterministic Python generator
that drops files into a Unity Catalog volume, exactly as real upstream systems would. The platform
then picks them up and moves them through the medallion layers (bronze → silver → gold).

The source data is intentionally messy: four file formats, encoding traps, CDC feeds, late arrivals,
duplicates and schema changes. Each episode deals with some of them.

## Repository layout

```
.
├── 00_kickoff.ipynb          # one-time workspace setup: Unity Catalog + history backfill
├── 01_reading_files.ipynb    # episode 1: exploring and reading the landing files (work in progress)
├── uc_bootstrap.py           # idempotent Unity Catalog bootstrap (catalogs, schemas, volumes)
├── config/
│   └── platform.yml          # the only place where catalog / schema / system names are defined
└── retail-simulator/
    └── simulator/            # source-system simulator (Python package)
```

## Unity Catalog layout

Everything is derived from `config/platform.yml`. With the default config (`project: moustache_markt`)
the bootstrap creates:

```
moustache_markt_sources                    "outside world", written only by the simulator
└── landing                                volumes: erp, crm, ecom, pos

moustache_markt_dev / moustache_markt_prod identical structure in each environment
├── bronze_erp, bronze_crm,                source-aligned, one schema per system
│   bronze_ecom, bronze_pos
├── silver, gold                           curated layers, shared by all systems
└── ops                                    volume: checkpoints (Auto Loader state, schema locations)
```

To rename the project, add an environment or a source system, edit `config/platform.yml`.
Names must be lower snake_case; the loader validates them before any SQL is generated.

## Getting started (Databricks)

Requirements: a Databricks workspace with Unity Catalog and **serverless** compute.

1. Add this repository as a **Git folder** in the Workspace.
2. Open `00_kickoff.ipynb` (it must stay in the repo root, next to `uc_bootstrap.py`).
3. Set the generation parameters in step 1 (`BACKFILL_START`, `BACKFILL_END`, `SCALE`).
4. Run the notebook top to bottom. It will:
   - print the SQL plan (dry-run),
   - create catalogs, schemas and volumes,
   - run a Parquet write smoke test,
   - backfill the history into `/Volumes/moustache_markt_sources/landing`,
   - show a per-table summary of what landed.

Everything is safe to re-run: DDL uses `IF NOT EXISTS`, the backfill skips itself when landing already
has data (override with `FORCE_BACKFILL = True`), and the generator is deterministic.

After pulling new simulator code into the Git folder, run `%restart_python` so the notebook picks it up.

## Unity Catalog bootstrap

`uc_bootstrap.py` turns `config/platform.yml` into an ordered list of idempotent DDL statements
(parent before child) and executes them with `spark.sql`.

```bash
python uc_bootstrap.py --dry-run                 # print the SQL plan only, no Spark needed
python uc_bootstrap.py                           # execute (Databricks job task / VS Code extension)
python uc_bootstrap.py --envs dev                # sources catalog + a single environment
python uc_bootstrap.py --config other.yml --dry-run
```

From a notebook, pass the arguments as a list: `uc_main(["--dry-run"])`, `uc_main([])`.

Requires PyYAML (preinstalled on Databricks Runtime; locally: `pip install pyyaml`).

## Retail simulator

`retail-simulator/simulator` generates daily files for four source systems. The simulated world is a
pure function of the config and the seed, so any single day can be regenerated on its own and
re-runs produce identical files.

| System | Tables | Format | What makes it interesting |
|---|---|---|---|
| **ERP** | `category`, `product`, `location` | Parquet, daily full snapshot | The "easy", typed source. Occasional numeric column exported as text. |
| **CRM** | `customer_cdc` | JSON Lines, CDC feed | Initial snapshot on go-live (2025-01-01), then I/U/D events. Messy e-mails and phone numbers. |
| **E-commerce** | `orders` | JSON array (API dump) | Needs `multiLine`. Nested line items. Only the latest version of an order per export. |
| **POS** | `receipt_line` | CSV, cp1252, `\|`-delimited | US thousands separators, 12-hour local timestamps, Windows line endings. No file on days when all stores are closed. |

Files land under `<output>/<system>/<table>/load_date=YYYY-MM-DD/`.

### Chaos layer

Built-in data quality problems, each decision keyed and reproducible:

- exact duplicate records within a file,
- late arrivals (records or whole store files 1-2 days late),
- dirty values: brand variants, invalid EINs, messy e-mails, unknown barcodes,
- accented names and symbols (José, Zoë, ™) that surface cp1252 vs UTF-8 bugs,
- **daily mode only:** numbers sent as text (`"$ 123"`, `"N/A"`) and Parquet type drift.
  These are off in the backfill on purpose, so that schema inference on the history is not silently widened to STRING.

### Schema versions

`--schema-version v2` simulates upstream changes: ERP `tax_rate` changes meaning (0.0625 → 6.25) and `weight_lb`
becomes `weight_oz`; CRM switches to Debezium-style `c/u/d/r` operations; e-commerce moves to JSON Lines with
epoch-millis timestamps; POS gets a new vendor with one UTF-8 file per store and renamed columns.

### Running the simulator

From a notebook (see `00_kickoff.ipynb`, step 2 for the `sys.path` setup):

```python
from simulator.cli import main as sim_main

sim_main(["backfill", "--start", "2025-01-01", "--end", "2025-01-30",
          "--scale", "0.2", "--output", "/Volumes/moustache_markt_sources/landing"])

sim_main(["daily", "--date", "2026-10-01", "--schema-version", "v2",
          "--output", "/Volumes/moustache_markt_sources/landing"])
```

Locally, from the `retail-simulator` folder (Parquet output requires `pyarrow`):

```bash
python -c "import sys; from simulator.cli import main; sys.exit(main(sys.argv[1:]))" \
    backfill --start 2025-01-01 --end 2025-01-07 --scale 0.05 --output ./sample-data
```

| Option | Default | Description |
|---|---|---|
| `--start` / `--end` | 2025-01-01 / required | Backfill date range (within 2025-01-01 .. 2027-12-31) |
| `--date` | required | Single day for `daily` mode |
| `--output` | required | Local folder or `/Volumes/<catalog>/<schema>` |
| `--systems` | `erp,crm,ecom,pos` | Comma-separated subset |
| `--scale` | `1.0` | Data volume multiplier (`1.0` ≈ 0.9 GB for the full history, `0.2` for quick runs) |
| `--schema-version` | `v1` | `v1` or `v2` |
| `--seed` | `42` | Random seed |
| `--type-corruption-rate` | 0 (backfill) / 0.003 (daily) | Share of numbers sent as text |
| `--parquet-type-drift-rate` | 0 (backfill) / 0.05 (daily) | Share of ERP files with cost as text |

## Episodes

| # | Notebook | Topic | Status |
|---|---|---|---|
| 00 | `00_kickoff.ipynb` | Workspace setup: Unity Catalog bootstrap and history backfill | done |
| 01 | `01_reading_files.ipynb` | Exploring the landing zone and reading raw files | in progress |

## License

[MIT](LICENSE) © 2026 Mateusz Wąsalski
