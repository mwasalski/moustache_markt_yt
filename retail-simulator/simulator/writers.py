"""Renders OutputFile objects to bytes and writes them (local folder or a Databricks Volume)."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path


@dataclass(frozen=True)
class CsvFormat:
    columns: tuple[str, ...]
    delimiter: str = ","
    encoding: str = "utf-8"
    line_terminator: str = "\n"


@dataclass(frozen=True)
class OutputFile:
    system: str
    table: str
    load_date: date
    filename: str
    fmt: str  # parquet | json_array | jsonl | csv
    rows: list
    schema: tuple[tuple[str, str], ...] | None = None  # parquet only: (column, type)
    csv_format: CsvFormat | None = None  # csv only

    @property
    def relative_path(self) -> Path:
        return Path(self.system, self.table, f"load_date={self.load_date:%Y-%m-%d}", self.filename)


def _json_default(value: object) -> object:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    raise TypeError(f"Not JSON serializable: {type(value).__name__}")


def _dumps(record: object) -> str:
    return json.dumps(record, ensure_ascii=False, separators=(",", ":"), default=_json_default)


def render_text(file: OutputFile) -> bytes:
    if file.fmt == "jsonl":
        return "".join(_dumps(row) + "\n" for row in file.rows).encode("utf-8")
    if file.fmt == "json_array":
        return ("[\n" + ",\n".join(_dumps(row) for row in file.rows) + "\n]\n").encode("utf-8")
    if file.fmt == "csv":
        spec = file.csv_format
        buffer = io.StringIO(newline="")
        writer = csv.writer(buffer, delimiter=spec.delimiter, lineterminator=spec.line_terminator)
        writer.writerow(spec.columns)
        writer.writerows(file.rows)
        return buffer.getvalue().encode(spec.encoding)
    raise ValueError(f"Not a text format: {file.fmt}")


def _arrow_type(pa, kind: str):
    if kind.startswith("decimal("):
        precision, scale = (int(part) for part in kind[len("decimal("):-1].split(","))
        return pa.decimal128(precision, scale)
    return {
        "int8": pa.int8(), "int16": pa.int16(), "int32": pa.int32(), "int64": pa.int64(),
        "string": pa.string(), "bool": pa.bool_(), "date": pa.date32(), "timestamp": pa.timestamp("us", tz="UTC"),
    }[kind]


def render_parquet(file: OutputFile) -> bytes:
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as error:  # preinstalled on Databricks
        raise ImportError("Parquet output needs pyarrow: pip install pyarrow") from error
    schema = pa.schema([(name, _arrow_type(pa, kind)) for name, kind in file.schema])
    sink = pa.BufferOutputStream()
    pq.write_table(pa.Table.from_pylist(file.rows, schema=schema), sink)
    return sink.getvalue().to_pybytes()


def write_file(file: OutputFile, root: Path) -> int:
    """One sequential write per file - Volumes (FUSE) do not support appends or random writes."""
    data = render_parquet(file) if file.fmt == "parquet" else render_text(file)
    path = Path(root) / file.relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return len(data)
