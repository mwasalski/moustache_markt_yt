# Metadata-driven pipelines: YAML z konfiguracją źródeł

Masz już ten wzorzec w repo: `config/platform.yml` + `load_config()` w `uc_bootstrap.py`. Wystarczy go przenieść na źródła danych.

## Najważniejsze: opcje readera to są metadane

Cztery funkcje `read_csv`, `read_json`, `read_jsonl` i `read_parquet` różnią się tylko dwiema rzeczami: formatem i opcjami. Spark przyjmuje jedno i drugie jako parametry:

```python
spark.read.format(fmt).options(**options).load(path)
```

Jeśli przeniesiesz format i opcje do YAML-a, cztery funkcje zamienią się w jedną. Nowe źródło dodasz wtedy wpisem w configu, bez pisania kodu. Na tym polega podejście metadata-driven.

## Propozycja: `config/sources.yml`

```yaml
# Source systems: how to read the files each system delivers.
# format / options = exactly what spark.read.format(...).options(...) expects.
#
# YAML trap: "|" must be quoted - unquoted, | starts a multi-line text block.

sources:
  erp:
    format: parquet            # schema is inside the file, no options needed

  crm:
    format: json               # JSON Lines = Spark's default json

  ecom:
    format: json
    options:
      multiLine: true          # the whole file is one JSON array

  pos:
    format: csv
    options:
      header: true
      sep: "|"
      encoding: cp1252
```

Zwróć uwagę, że nie ma tu `json_array` ani `jsonl` jak w obecnym `FORMATS`. Lepiej używać nazw formatów ze Sparka niż własnego słownika. Wtedy nie potrzebujesz żadnego tłumaczenia między configiem a kodem, a „to jest tablica JSON” zapisujesz jako opcję `multiLine: true`.

## W notebooku

```python
import yaml

with open("config/sources.yml") as f:
    SOURCES_CONFIG = yaml.safe_load(f)["sources"]


def read_source(system, path):
    source = SOURCES_CONFIG[system]
    return spark.read.format(source["format"]).options(**source.get("options", {})).load(path)


for volume in DATA_VOLUMES:
    system = volume["full_name"].split(".")[-1]          # erp, crm, ...
    for folder in volume["entries"]:
        first_day = dbutils.fs.ls(f"{volume['path']}/{folder}")[0].path
        sample = dbutils.fs.ls(first_day)[0].path
        print(f"{system}/{folder}: {sample}")
        display(read_source(system, sample).limit(10))
```

Rozszerzenie pliku przestaje być potrzebne: o tym, jak czytać, decyduje config, a nie nazwa pliku. To bezpieczniejsze, bo plik `.json` z ecom i plik `.jsonl` z CRM czyta się inaczej, a `.csv` z POS v1 i v2 też różnią się opcjami.

## Co można przenieść do YAML-a później

Gdy pierwszy krok zadziała, ten sam plik może sterować kolejnymi warstwami:

| Klucz | Do czego | Kiedy |
|---|---|---|
| `tables:` z nadpisaniem opcji per tabela | gdy jedna tabela w systemie czyta się inaczej niż reszta | od razu, jeśli potrzeba |
| `target:` / `load_mode: overwrite \| append` | notebook 02 nie musi znać nazw tabel w bronze | odcinek z bronze |
| `schema_hints:` | typy z raportu w notebooku 03 (np. `item_price DECIMAL(10,2)`) jako `cloudFiles.schemaHints` | Auto Loader |
| `primary_key:`, `cdc_column:` | deduplikacja i MERGE w silver (CRM `_op`) | silver |
| `expectations:` | reguły jakości danych (`ean IS NOT NULL`) | silver / DQ |

## Discovery a config

W `01` odkrywasz, co jest w landingu. Pipeline powinien natomiast czytać tylko to, co jest w configu: jawnie, wersjonowane w Git i sprawdzane w PR. Te dwie rzeczy dobrze się uzupełniają. Prosty check „foldery w landingu, których nie ma w `sources.yml`” wyłapie nową tabelę, zanim ktoś się zdziwi, że jej nie ma w bronze.

YAML w repo ma przewagę nad tabelą metadanych w Delta właśnie przez to, że idzie przez Git i code review. Job `uc-plan` w CI może go walidować tak samo jak `platform.yml`.

## Do zrobienia

- [ ] dodać `config/sources.yml`
- [ ] przepiąć `01_reading_files` (komórka `read_all_files`) na `read_source()`
- [ ] przepiąć `02_bronze_tables` na `read_source()`
