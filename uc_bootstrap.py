"""Idempotent Unity Catalog bootstrap for the retail platform: catalogs, schemas, volumes.

Usage:
    python uc_bootstrap.py --dry-run      # print the SQL plan, no Spark needed
    python uc_bootstrap.py                # run on Databricks (job task / VS Code extension)
    python uc_bootstrap.py --envs dev     # shared sources + a single environment only
    python uc_bootstrap.py --config other.yml --dry-run   # a different config file

Configuration (project name, environments, systems, layers): config/platform.yml.
"""
# Module docstring (above) - the first value in the file, ends up in `uc_bootstrap.__doc__`
# and shows up in `help(uc_bootstrap)`. Usage details: README_uc_bootstrap.md.

# Type annotations are treated as strings and are not evaluated at runtime.
# Thanks to that, syntax like `str | None` or `tuple[str, ...]` also works on older
# Python and costs nothing at import time. This import must be the first statement in the file.
from __future__ import annotations

# argparse - the standard command-line argument parser (--dry-run, --envs, --config).
import argparse
# logging - standard logging; on Databricks the logs go to the job/notebook output.
import logging
# re - regular expressions, used to validate Unity Catalog object names.
import re
# Abstract collection types used only in annotations:
#   Callable - "something that can be called" (here: a function executing SQL, e.g. spark.sql),
#   Iterable - "something that can be iterated over" (list, generator, tuple...),
#   Sequence - an iterable with indexing and a length (list, tuple).
from collections.abc import Callable, Iterable, Sequence
# dataclass - a decorator generating __init__, __repr__, __eq__ from the class fields.
# fields - returns the list of dataclass fields; we use it to know which keys to expect in the YAML.
from dataclasses import dataclass, fields
# Path - an object-oriented file path; works the same on Windows, Linux and in the Databricks Workspace.
from pathlib import Path
# Any - "any type"; this is how we describe raw YAML data before validating it.
from typing import Any

# PyYAML - a YAML file parser. External package (pip install pyyaml), preinstalled on Databricks Runtime.
import yaml

# Logger named after the module ("uc_bootstrap", or "__main__" when run as a script).
# On its own it prints nothing - only logging.basicConfig() in main() attaches a handler.
logger = logging.getLogger(__name__)

# Default config file, resolved relative to THIS file (__file__), not the working directory.
# The working directory differs in a terminal, a notebook and a job - __file__ is always the same.
# resolve() makes the path absolute, .parent is the folder containing uc_bootstrap.py, "/" joins paths.
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "config" / "platform.yml"

# Fixed object names that do not depend on the config. Kept in one place because they are used
# both by the DDL statements and by the volume paths (landing_path, checkpoints_path).
LANDING_SCHEMA = "landing"
OPS_SCHEMA = "ops"
CHECKPOINTS_VOLUME = "checkpoints"

# Regex for a valid UC object name, compiled once (at module level):
#   ^        - start of the string,
#   [a-z]    - the first character is a lowercase letter (not a digit, not an underscore),
#   [a-z0-9_]* - followed by any number of lowercase letters, digits or "_",
#   $        - end of the string (nothing else may follow).
# In other words: lower snake_case. Rejects uppercase letters, hyphens, spaces, dots, quotes, semicolons.
UC_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]*$")


# frozen=True -> the instance is immutable (assigning to a field raises FrozenInstanceError)
# and hashable. The platform config should not change while the script is running.
# The fields have NO default values: the only source of values is config/platform.yml.
# If defaults lived both here and in the YAML, sooner or later they would drift apart.
@dataclass(frozen=True)
class PlatformConfig:
    # Prefix of all catalogs, e.g. "moustache_markt" -> moustache_markt_sources, moustache_markt_dev.
    project: str
    # Environments that each get a separate catalog. A tuple (not a list) because it is
    # immutable - it fits frozen=True (a list could be modified "from the inside").
    environments: tuple[str, ...]
    # Source systems - each gets a volume in landing and a bronze_<system> schema in every env.
    source_systems: tuple[str, ...]
    # "Cleaned" (medallion) layers - shared by all systems, one schema each.
    curated_layers: tuple[str, ...]

    # @property -> called without parentheses: config.sources_catalog.
    # The name is derived from `project`, so it cannot get out of sync with the prefix.
    @property
    def sources_catalog(self) -> str:
        # The "outside world" catalog - a single one, shared by all environments.
        return f"{self.project}_sources"

    # A regular method, because it needs an argument (the environment name).
    def env_catalog(self, env: str) -> str:
        # The data platform catalog for a given environment, e.g. "moustache_markt_dev".
        return f"{self.project}_{env}"

    # File path to landing, e.g. "/Volumes/moustache_markt_sources/landing".
    # UC volumes are visible as regular folders under /Volumes/<catalog>/<schema>/<volume>.
    # Below it sit the per-system volumes (erp, crm, ...) - that is where the simulator writes files.
    @property
    def landing_path(self) -> str:
        return f"/Volumes/{self.sources_catalog}/{LANDING_SCHEMA}"

    # Path to the volume holding Auto Loader checkpoints in a given environment,
    # e.g. "/Volumes/moustache_markt_dev/ops/checkpoints".
    def checkpoints_path(self, env: str) -> str:
        return f"/Volumes/{self.env_catalog(env)}/{OPS_SCHEMA}/{CHECKPOINTS_VOLUME}"


# Checks a single list of names from the YAML and turns it into a tuple.
# `source` is the file name - it goes into the error message so you know where to look.
def _name_list(raw: dict[str, Any], key: str, source: str) -> tuple[str, ...]:
    # The value under the given key (presence of the key is already checked by _config_from_dict).
    value = raw[key]
    # Must be a list. A plain string is iterable too: "erp" would yield systems "e", "r", "p".
    if not isinstance(value, list) or not value:
        raise ValueError(f"{source}: '{key}' must be a non-empty list, got {value!r}")
    # Every element must be a string. Catches, among others, the YAML trap: unquoted `no` is False, not "no".
    not_strings = [item for item in value if not isinstance(item, str)]
    if not_strings:
        raise ValueError(f"{source}: '{key}' must contain only strings, got {not_strings!r}")
    # Duplicates are almost certainly a mistake ("erp" twice = the same CREATE twice).
    # set() removes repetitions, so a different length means some name is repeated.
    if len(set(value)) != len(value):
        raise ValueError(f"{source}: '{key}' contains duplicates: {value!r}")
    # A tuple instead of a list - see the comment on PlatformConfig.
    return tuple(value)


# Turns the raw YAML parse result (any type) into a validated PlatformConfig.
# Split out of load_config so that tests can pass a dict without creating a file.
def _config_from_dict(raw: Any, source: str) -> PlatformConfig:
    # The file must be a "key: value" mapping. An empty file gives None, a bare list gives list.
    if not isinstance(raw, dict):
        raise ValueError(f"{source}: expected a mapping of keys to values, got {type(raw).__name__}")
    # Expected keys = the dataclass field names. Adding a field to PlatformConfig automatically
    # makes it required in the YAML - no need to remember to update a separate list.
    expected = {field.name for field in fields(PlatformConfig)}
    # Set differences: extra keys (e.g. the typo "enviroments") and missing ones.
    # str() in case of non-string keys (e.g. `1: x` in YAML) - otherwise sorted() would blow up.
    unknown = sorted(str(key) for key in raw.keys() - expected)
    missing = sorted(expected - raw.keys())
    # A typo in a key is reported as an error - silently ignored, it would cause a hard-to-find bug.
    if unknown or missing:
        raise ValueError(f"{source}: unknown keys {unknown}, missing keys {missing}")
    # project is a single string, not a list.
    if not isinstance(raw["project"], str):
        raise ValueError(f"{source}: 'project' must be a string, got {raw['project']!r}")
    # Build the immutable object. Validity of the names themselves (snake_case) is checked later
    # by _identifier() in build_statements - one place for name validation instead of two.
    return PlatformConfig(
        project=raw["project"],
        environments=_name_list(raw, "environments", source),
        source_systems=_name_list(raw, "source_systems", source),
        curated_layers=_name_list(raw, "curated_layers", source),
    )


# Public API: reads the YAML file and returns a validated config.
# Accepts str or Path; defaults to config/platform.yml next to this module.
def load_config(path: str | Path = DEFAULT_CONFIG_PATH) -> PlatformConfig:
    """Reads and validates the platform config from a YAML file."""
    # Path(...) on a Path is safe - it returns an equivalent path.
    path = Path(path)
    # encoding="utf-8" explicitly: on Windows the default encoding is cp1250/cp1252 and non-ASCII
    # characters in YAML comments would get mangled. Missing file -> FileNotFoundError with the full path.
    with path.open(encoding="utf-8") as file:
        # safe_load, NEVER yaml.load: plain load can construct arbitrary Python objects
        # from a crafted file. safe_load returns only dict/list/str/int/float/bool/None.
        raw = yaml.safe_load(file)
    # Validate and build the object; the file name goes into error messages.
    return _config_from_dict(raw, source=str(path))


# A leading underscore in the name = a "private" module function (a convention, not enforced).
def _identifier(name: str) -> str:
    """Rejects anything that is not lower snake_case (typos, hyphens, SQL injection)."""
    # match() checks for a match from the start of the string; thanks to "$" in the regex - to the very end.
    # Returns None when the name does not match.
    if not UC_IDENTIFIER.match(name):
        # !r inserts the repr() of the value - with quotes, so e.g. trailing spaces are visible.
        raise ValueError(f"Invalid UC identifier: {name!r}")
    # Return the same name so the function can be used "inline" inside an f-string.
    return name


# Builds the DDL for the sources catalog: catalog -> landing schema -> one volume per system.
def _sources_statements(config: PlatformConfig) -> list[str]:
    # Catalog name after validation, e.g. "moustache_markt_sources".
    catalog = _identifier(config.sources_catalog)
    # Initial list: parent (catalog) first, then child (schema).
    statements = [
        # Python concatenates two adjacent string literals into one (no "+").
        # IF NOT EXISTS -> re-running breaks nothing (idempotency).
        f"CREATE CATALOG IF NOT EXISTS {catalog} "
        "COMMENT 'Simulated outside world. Written only by the simulator.'",
        # The "landing" schema in the sources catalog - raw files land here.
        f"CREATE SCHEMA IF NOT EXISTS {catalog}.{LANDING_SCHEMA} "
        "COMMENT 'Raw files delivered by source systems'",
    ]
    # += on a list appends the elements of another list (like extend).
    statements += [
        # Volume = a file directory in UC, path /Volumes/<catalog>/landing/<system> (= landing_path/<system>).
        # The system name is validated because it goes straight into SQL.
        f"CREATE VOLUME IF NOT EXISTS {catalog}.{LANDING_SCHEMA}.{_identifier(system)} "
        f"COMMENT 'Landing zone for source system: {system}'"
        # List comprehension - one statement per system, in config order.
        for system in config.source_systems
    ]
    # Result: 2 + len(source_systems) statements (6 by default).
    return statements


# Builds the DDL for a single environment (dev or prod).
def _environment_statements(config: PlatformConfig, env: str) -> list[str]:
    # Environment catalog name after validation, e.g. "moustache_markt_dev".
    catalog = _identifier(config.env_catalog(env))
    # The catalog itself first - everything below is its child.
    statements = [
        f"CREATE CATALOG IF NOT EXISTS {catalog} COMMENT 'Data platform, environment: {env}'"
    ]
    # A bronze schema per source system (bronze_erp, bronze_crm, ...).
    # Bronze is "source-aligned": one schema = one system, data 1:1 from the source.
    statements += [
        # Validate the whole concatenated name 'bronze_' + system.
        f"CREATE SCHEMA IF NOT EXISTS {catalog}.{_identifier('bronze_' + system)} "
        f"COMMENT 'Bronze, source-aligned: {system}'"
        for system in config.source_systems
    ]
    # Curated layer schemas (silver, gold) - shared by all systems.
    statements += [
        # capitalize() -> turns "silver" into "Silver" in the comment.
        f"CREATE SCHEMA IF NOT EXISTS {catalog}.{_identifier(layer)} "
        f"COMMENT '{layer.capitalize()} layer'"
        for layer in config.curated_layers
    ]
    # The technical "ops" schema and a volume for checkpoints (schema before volume - parent before child).
    statements += [
        f"CREATE SCHEMA IF NOT EXISTS {catalog}.{OPS_SCHEMA} "
        "COMMENT 'Operational metadata: checkpoints, DQ results, run logs'",
        # Auto Loader keeps the stream state here (which files it has already read) and the inferred schema.
        f"CREATE VOLUME IF NOT EXISTS {catalog}.{OPS_SCHEMA}.{CHECKPOINTS_VOLUME} "
        "COMMENT 'Auto Loader checkpoints and schema locations'",
    ]
    # Result: 1 + len(source_systems) + len(curated_layers) + 2 statements (9 by default).
    return statements


# The module's public API: turns the config into a complete, ordered list of SQL statements.
# envs=None means "all environments from the config".
def build_statements(config: PlatformConfig, envs: Sequence[str] | None = None) -> list[str]:
    """Pure function: config -> ordered, idempotent DDL. Parent always before child."""
    # Pure function = no side effects, same input -> same output; easy to test.
    # Empty list or None -> take all environments; otherwise a copy as a tuple.
    selected_envs = tuple(envs) if envs else config.environments
    # Set difference: environments given by the user that are not in the config.
    # sorted() gives a stable, readable order in the error message.
    unknown = sorted(set(selected_envs) - set(config.environments))
    # A non-empty list is "truthy" -> there are unknown environments.
    if unknown:
        # Fail fast, before any SQL is generated/executed.
        raise ValueError(f"Unknown environments: {unknown}")

    # The sources catalog always comes first and is always created (also with --envs dev).
    statements = _sources_statements(config)
    # Then each selected environment in turn, in the order given by the user.
    for env in selected_envs:
        statements += _environment_statements(config, env)
    # By default: 6 + 9 * 2 = 24 statements.
    return statements


# Executes the statements. `execute` is injected (dependency injection), so this function
# knows nothing about Spark - in tests you can pass e.g. list.append.
def apply_statements(statements: Iterable[str], execute: Callable[[str], object]) -> int:
    """Executes the statements in order. `execute` is spark.sql on Databricks, and a stub in tests."""
    # Counter of executed statements - returned at the end for the summary log.
    executed = 0
    # Strictly sequential: order matters (parent before child).
    for statement in statements:
        # Log first, then execute - if the statement fails, the log shows which one.
        logger.info(statement)
        # The result (e.g. a DataFrame from spark.sql) is ignored - DDL returns nothing of interest.
        # An exception from execute stops the loop; earlier statements stay executed,
        # which is safe because everything is idempotent and you can simply run it again.
        execute(statement)
        # Increment the counter only after a successful execution.
        executed += 1
    return executed


# CLI entry point. argv=None -> argparse reads sys.argv[1:]; in tests you can pass a list.
def main(argv: Sequence[str] | None = None) -> None:
    # Parser with a description shown in `--help`.
    parser = argparse.ArgumentParser(description="Idempotent Unity Catalog bootstrap")
    # nargs="+" -> one or more values: --envs dev  or  --envs dev prod.
    # No flag -> args.envs == None -> all environments.
    parser.add_argument("--envs", nargs="+", help="Subset of environments, e.g. --envs dev")
    # store_true -> a flag without a value; present = True, absent = False.
    # argparse turns the hyphen into an underscore: --dry-run -> args.dry_run.
    parser.add_argument("--dry-run", action="store_true", help="Print the SQL plan only")
    # type=Path -> argparse converts the given string to a Path right away.
    # Defaults to config/platform.yml next to this module, so a job does not need to pass the flag.
    parser.add_argument(
        "--config", type=Path, default=DEFAULT_CONFIG_PATH,
        help=f"Path to the platform YAML config (default: {DEFAULT_CONFIG_PATH.name} next to this script)",
    )
    # Parsing; on invalid arguments argparse prints the error itself and exits (exit code 2).
    args = parser.parse_args(argv)

    # Load and validate the YAML - a broken file stops the script before any SQL is built.
    config = load_config(args.config)
    # The SQL plan is always built, also in dry-run mode - so validation (names, environments)
    # works locally, without Spark.
    statements = build_statements(config, args.envs)
    # "Dry" mode: just print the plan and exit.
    if args.dry_run:
        # One statement per line, to stdout (print, not logger - no timestamps, easy to redirect to a file).
        print("\n".join(statements))
        # Exit before importing pyspark - dry-run works without Spark installed.
        return

    # Logging is configured only in execution mode: INFO level, format with time and level.
    # force=True removes previously attached handlers (Databricks/IPython often already has some),
    # otherwise basicConfig would be silently ignored and the logs would not show up.
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", force=True)
    from pyspark.sql import SparkSession  # lazy import: dry-run and unit tests do not need Spark

    # On Databricks returns the existing session (the notebook/job already has one); locally via
    # Databricks Connect / the VS Code extension - a remote session.
    spark = SparkSession.builder.getOrCreate()
    # Pass the spark.sql method (without calling it!) as the executing function.
    executed = apply_statements(statements, spark.sql)
    # Summary; %d + argument instead of an f-string - lazy formatting, done only when the log is emitted.
    logger.info("Done: %d statements executed", executed)


# This block runs only when the file is executed as a script (python uc_bootstrap.py),
# not on import (e.g. `from uc_bootstrap import build_statements` in tests).
if __name__ == "__main__":
    main()
