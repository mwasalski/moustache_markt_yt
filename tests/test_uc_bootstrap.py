"""Unit tests for uc_bootstrap.py - no Spark needed, SQL execution is stubbed with list.append."""

from __future__ import annotations

import pytest

from uc_bootstrap import apply_statements, build_statements, load_config, main


@pytest.fixture
def write_config(tmp_path):
    """Writes a platform.yml variant and returns its path."""
    def write(project="moustache_markt", source_systems="[erp, crm]"):
        path = tmp_path / "platform.yml"
        path.write_text(
            f"project: {project}\n"
            "environments: [dev, prod]\n"
            f"source_systems: {source_systems}\n"
            "curated_layers: [silver, gold]\n",
            encoding="utf-8",
        )
        return path
    return write


def test_default_config_plans_24_statements():
    statements = build_statements(load_config())
    assert len(statements) == 24
    # Parent before child: the sources catalog is created first.
    assert statements[0].startswith("CREATE CATALOG IF NOT EXISTS moustache_markt_sources")


def test_envs_subset_keeps_sources_catalog():
    statements = build_statements(load_config(), envs=["dev"])
    assert len(statements) == 15
    assert not any("moustache_markt_prod" in statement for statement in statements)


def test_unknown_env_is_rejected():
    with pytest.raises(ValueError, match="Unknown environments"):
        build_statements(load_config(), envs=["qa"])


def test_invalid_identifier_is_rejected(write_config):
    config = load_config(write_config(project="Moustache-Markt"))
    with pytest.raises(ValueError, match="Invalid UC identifier"):
        build_statements(config)


def test_yaml_boolean_trap_is_rejected(write_config):
    # Unquoted `no` is a YAML boolean, not the string "no".
    with pytest.raises(ValueError, match="only strings"):
        load_config(write_config(source_systems="[erp, no]"))


def test_apply_statements_runs_in_order():
    executed: list[str] = []
    assert apply_statements(["A", "B", "C"], executed.append) == 3
    assert executed == ["A", "B", "C"]


def test_dry_run_prints_plan(capsys):
    main(["--dry-run"])
    assert len(capsys.readouterr().out.strip().splitlines()) == 24
