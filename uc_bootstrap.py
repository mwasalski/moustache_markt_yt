"""Idempotentny bootstrap Unity Catalog dla platformy retail: katalogi, schematy, volumes.

Użycie:
    python uc_bootstrap.py --dry-run      # wypisz plan SQL, Spark niepotrzebny
    python uc_bootstrap.py                # uruchom na Databricks (task joba / rozszerzenie VS Code)
    python uc_bootstrap.py --envs dev     # wspólne źródła + tylko jedno środowisko
    python uc_bootstrap.py --config inny.yml --dry-run   # inny plik konfiguracji

Konfiguracja (nazwa projektu, środowiska, systemy, warstwy): config/platform.yml.
"""
# Docstring modułu (powyżej) - pierwsza wartość w pliku, trafia do `uc_bootstrap.__doc__`
# i pokazuje się w `help(uc_bootstrap)`. Szczegóły użycia: README_uc_bootstrap.md.

# Adnotacje typów są traktowane jako napisy i nie są wyliczane w runtime.
# Dzięki temu składnia typu `str | None` czy `tuple[str, ...]` działa także na starszym
# Pythonie i nie kosztuje nic przy imporcie. Ten import musi być pierwszą instrukcją w pliku.
from __future__ import annotations

# argparse - standardowy parser argumentów linii poleceń (--dry-run, --envs, --config).
import argparse
# logging - standardowe logowanie; na Databricks logi trafiają do outputu joba/notebooka.
import logging
# re - wyrażenia regularne, używane do walidacji nazw obiektów Unity Catalog.
import re
# Abstrakcyjne typy kolekcji używane wyłącznie w adnotacjach:
#   Callable - "coś, co można wywołać" (tu: funkcja wykonująca SQL, np. spark.sql),
#   Iterable - "coś, po czym można iterować" (lista, generator, krotka...),
#   Sequence - iterowalne z indeksowaniem i długością (lista, krotka).
from collections.abc import Callable, Iterable, Sequence
# dataclass - dekorator generujący __init__, __repr__, __eq__ na podstawie pól klasy.
# fields - zwraca listę pól dataclassy; używamy jej, żeby wiedzieć, jakich kluczy oczekiwać w YAML.
from dataclasses import dataclass, fields
# Path - obiektowa ścieżka do pliku; działa tak samo na Windows, Linuksie i w Workspace Databricks.
from pathlib import Path
# Any - "dowolny typ"; tak opisujemy surowe dane z YAML, zanim je zwalidujemy.
from typing import Any

# PyYAML - parser plików YAML. Zewnętrzna paczka (pip install pyyaml), preinstalowana na Databricks Runtime.
import yaml

# Logger nazwany nazwą modułu ("uc_bootstrap" albo "__main__" przy uruchomieniu skryptu).
# Sam w sobie nic nie wypisuje - dopiero logging.basicConfig() w main() podpina handler.
logger = logging.getLogger(__name__)

# Domyślny plik konfiguracji, liczony względem TEGO pliku (__file__), a nie katalogu roboczego.
# Katalog roboczy jest inny w terminalu, w notebooku i w jobie - __file__ jest zawsze ten sam.
# resolve() zamienia ścieżkę na absolutną, .parent to folder z uc_bootstrap.py, "/" skleja ścieżki.
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "config" / "platform.yml"

# Stałe nazwy obiektów, które nie zależą od konfiguracji. Trzymane w jednym miejscu, bo używają
# ich zarówno polecenia DDL, jak i ścieżki do volumes (landing_path, checkpoints_path).
LANDING_SCHEMA = "landing"
OPS_SCHEMA = "ops"
CHECKPOINTS_VOLUME = "checkpoints"

# Skompilowany raz (na poziomie modułu) regex poprawnej nazwy obiektu UC:
#   ^        - początek napisu,
#   [a-z]    - pierwszy znak to mała litera (nie cyfra, nie podkreślnik),
#   [a-z0-9_]* - dalej dowolnie wiele małych liter, cyfr lub "_",
#   $        - koniec napisu (nic więcej nie może się pojawić).
# Czyli: lower snake_case. Odrzuca wielkie litery, myślniki, spacje, kropki, cudzysłowy, średniki.
UC_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]*$")


# frozen=True -> instancja jest niemutowalna (przypisanie do pola rzuca FrozenInstanceError)
# i hashowalna. Konfiguracja platformy nie powinna się zmieniać w trakcie działania skryptu.
# Pola NIE mają wartości domyślnych: jedynym źródłem wartości jest config/platform.yml.
# Gdyby domyślne były i tu, i w YAML, prędzej czy później by się rozjechały.
@dataclass(frozen=True)
class PlatformConfig:
    # Prefiks wszystkich katalogów, np. "moustache_markt" -> moustache_markt_sources, moustache_markt_dev.
    project: str
    # Środowiska, dla których powstanie osobny katalog. Krotka (a nie lista), bo jest
    # niemutowalna - pasuje do frozen=True (listę dałoby się zmienić "od środka").
    environments: tuple[str, ...]
    # Systemy źródłowe - każdy dostaje volume w landingu i schemat bronze_<system> w każdym env.
    source_systems: tuple[str, ...]
    # Warstwy "wyczyszczone" (medallion) - wspólne dla wszystkich systemów, po jednym schemacie.
    curated_layers: tuple[str, ...]

    # @property -> wywołujemy bez nawiasów: config.sources_catalog.
    # Nazwa jest wyliczana z `project`, więc nie da się jej rozsynchronizować z prefiksem.
    @property
    def sources_catalog(self) -> str:
        # Katalog "świata zewnętrznego" - jeden, wspólny dla wszystkich środowisk.
        return f"{self.project}_sources"

    # Zwykła metoda, bo potrzebuje argumentu (nazwy środowiska).
    def env_catalog(self, env: str) -> str:
        # Katalog platformy danych dla danego środowiska, np. "moustache_markt_dev".
        return f"{self.project}_{env}"

    # Ścieżka plikowa do landingu, np. "/Volumes/moustache_markt_sources/landing".
    # Volumes w UC są widoczne jak zwykłe foldery pod /Volumes/<katalog>/<schemat>/<volume>.
    # Pod nią leżą volumes per system (erp, crm, ...) - tam symulator zapisuje pliki.
    @property
    def landing_path(self) -> str:
        return f"/Volumes/{self.sources_catalog}/{LANDING_SCHEMA}"

    # Ścieżka do volume z checkpointami Auto Loadera w danym środowisku,
    # np. "/Volumes/moustache_markt_dev/ops/checkpoints".
    def checkpoints_path(self, env: str) -> str:
        return f"/Volumes/{self.env_catalog(env)}/{OPS_SCHEMA}/{CHECKPOINTS_VOLUME}"


# Sprawdza jedną listę nazw z YAML i zamienia ją na krotkę.
# `source` to nazwa pliku - trafia do komunikatu błędu, żeby było wiadomo, gdzie szukać.
def _name_list(raw: dict[str, Any], key: str, source: str) -> tuple[str, ...]:
    # Wartość pod danym kluczem (obecność klucza sprawdza już wcześniej _config_from_dict).
    value = raw[key]
    # Musi być lista. Sam napis też by się dał iterować: "erp" dałby systemy "e", "r", "p".
    if not isinstance(value, list) or not value:
        raise ValueError(f"{source}: '{key}' must be a non-empty list, got {value!r}")
    # Każdy element musi być napisem. Łapie m.in. pułapkę YAML: niecytowane `no` to False, a nie "no".
    not_strings = [item for item in value if not isinstance(item, str)]
    if not_strings:
        raise ValueError(f"{source}: '{key}' must contain only strings, got {not_strings!r}")
    # Duplikaty to prawie na pewno pomyłka (dwa razy "erp" = dwa razy ten sam CREATE).
    # set() usuwa powtórzenia, więc różna długość oznacza, że jakaś nazwa się powtarza.
    if len(set(value)) != len(value):
        raise ValueError(f"{source}: '{key}' contains duplicates: {value!r}")
    # Krotka zamiast listy - patrz komentarz przy PlatformConfig.
    return tuple(value)


# Zamienia surowy wynik parsowania YAML (dowolny typ) na zwalidowany PlatformConfig.
# Wydzielone z load_config, żeby testy mogły podać słownik bez tworzenia pliku.
def _config_from_dict(raw: Any, source: str) -> PlatformConfig:
    # Plik musi być mapą "klucz: wartość". Pusty plik daje None, sama lista daje list.
    if not isinstance(raw, dict):
        raise ValueError(f"{source}: expected a mapping of keys to values, got {type(raw).__name__}")
    # Oczekiwane klucze = nazwy pól dataclassy. Dodanie pola do PlatformConfig automatycznie
    # czyni je wymaganym w YAML - nie trzeba pamiętać o aktualizacji osobnej listy.
    expected = {field.name for field in fields(PlatformConfig)}
    # Różnice zbiorów: klucze nadmiarowe (np. literówka "enviroments") i brakujące.
    # str() na wypadek kluczy niebędących napisami (np. `1: x` w YAML) - inaczej sorted() by się wywalił.
    unknown = sorted(str(key) for key in raw.keys() - expected)
    missing = sorted(expected - raw.keys())
    # Literówkę w kluczu zgłaszamy jako błąd - po cichu zignorowana dałaby trudny do znalezienia bug.
    if unknown or missing:
        raise ValueError(f"{source}: unknown keys {unknown}, missing keys {missing}")
    # project to pojedynczy napis, a nie lista.
    if not isinstance(raw["project"], str):
        raise ValueError(f"{source}: 'project' must be a string, got {raw['project']!r}")
    # Budujemy niemutowalny obiekt. Poprawność samych nazw (snake_case) sprawdza później
    # _identifier() w build_statements - jedno miejsce walidacji nazw zamiast dwóch.
    return PlatformConfig(
        project=raw["project"],
        environments=_name_list(raw, "environments", source),
        source_systems=_name_list(raw, "source_systems", source),
        curated_layers=_name_list(raw, "curated_layers", source),
    )


# Publiczne API: wczytuje plik YAML i zwraca zwalidowaną konfigurację.
# Przyjmuje str albo Path; domyślnie config/platform.yml obok tego modułu.
def load_config(path: str | Path = DEFAULT_CONFIG_PATH) -> PlatformConfig:
    """Wczytuje i waliduje konfigurację platformy z pliku YAML."""
    # Path(...) na Path jest bezpieczne - zwraca równoważną ścieżkę.
    path = Path(path)
    # encoding="utf-8" jawnie: na Windows domyślne kodowanie to cp1250/cp1252 i polskie znaki
    # w komentarzach YAML by się rozsypały. Brak pliku -> FileNotFoundError z pełną ścieżką.
    with path.open(encoding="utf-8") as file:
        # safe_load, NIGDY yaml.load: zwykły load potrafi tworzyć dowolne obiekty Pythona
        # z odpowiednio spreparowanego pliku. safe_load zwraca tylko dict/list/str/int/float/bool/None.
        raw = yaml.safe_load(file)
    # Walidacja i budowa obiektu; nazwa pliku idzie do komunikatów błędów.
    return _config_from_dict(raw, source=str(path))


# Podkreślnik na początku nazwy = funkcja "prywatna" modułu (konwencja, nie wymuszenie).
def _identifier(name: str) -> str:
    """Odrzuca wszystko, co nie jest lower snake_case (literówki, myślniki, SQL injection)."""
    # match() sprawdza dopasowanie od początku napisu; dzięki "$" w regexie - do samego końca.
    # Zwraca None, gdy nazwa nie pasuje.
    if not UC_IDENTIFIER.match(name):
        # !r wstawia repr() wartości - z cudzysłowami, więc widać np. spacje na końcu.
        raise ValueError(f"Invalid UC identifier: {name!r}")
    # Zwracamy tę samą nazwę, żeby dało się użyć funkcji "w locie" wewnątrz f-stringa.
    return name


# Buduje DDL dla katalogu źródłowego: katalog -> schemat landing -> volume na każdy system.
def _sources_statements(config: PlatformConfig) -> list[str]:
    # Nazwa katalogu po walidacji, np. "moustache_markt_sources".
    catalog = _identifier(config.sources_catalog)
    # Lista startowa: najpierw rodzic (katalog), potem dziecko (schemat).
    statements = [
        # Dwa sąsiadujące literały napisowe Python skleja w jeden (bez "+").
        # IF NOT EXISTS -> ponowne uruchomienie nic nie psuje (idempotencja).
        f"CREATE CATALOG IF NOT EXISTS {catalog} "
        "COMMENT 'Simulated outside world. Written only by the simulator.'",
        # Schemat "landing" w katalogu źródłowym - tu wpadają surowe pliki.
        f"CREATE SCHEMA IF NOT EXISTS {catalog}.{LANDING_SCHEMA} "
        "COMMENT 'Raw files delivered by source systems'",
    ]
    # += na liście dokleja elementy z drugiej listy (jak extend).
    statements += [
        # Volume = katalog plików w UC, ścieżka /Volumes/<catalog>/landing/<system> (= landing_path/<system>).
        # Nazwa systemu jest walidowana, bo trafia bezpośrednio do SQL.
        f"CREATE VOLUME IF NOT EXISTS {catalog}.{LANDING_SCHEMA}.{_identifier(system)} "
        f"COMMENT 'Landing zone for source system: {system}'"
        # List comprehension - jedno polecenie na każdy system, w kolejności z konfiguracji.
        for system in config.source_systems
    ]
    # Wynik: 2 + len(source_systems) poleceń (domyślnie 6).
    return statements


# Buduje DDL dla jednego środowiska (dev albo prod).
def _environment_statements(config: PlatformConfig, env: str) -> list[str]:
    # Nazwa katalogu środowiska po walidacji, np. "moustache_markt_dev".
    catalog = _identifier(config.env_catalog(env))
    # Najpierw sam katalog - wszystko poniżej jest jego dzieckiem.
    statements = [
        f"CREATE CATALOG IF NOT EXISTS {catalog} COMMENT 'Data platform, environment: {env}'"
    ]
    # Schemat bronze per system źródłowy (bronze_erp, bronze_crm, ...).
    # Bronze jest "source-aligned": jeden schemat = jeden system, dane 1:1 ze źródła.
    statements += [
        # Walidujemy całą sklejoną nazwę 'bronze_' + system.
        f"CREATE SCHEMA IF NOT EXISTS {catalog}.{_identifier('bronze_' + system)} "
        f"COMMENT 'Bronze, source-aligned: {system}'"
        for system in config.source_systems
    ]
    # Schematy warstw curated (silver, gold) - wspólne dla wszystkich systemów.
    statements += [
        # capitalize() -> "silver" zamienia na "Silver" w komentarzu.
        f"CREATE SCHEMA IF NOT EXISTS {catalog}.{_identifier(layer)} "
        f"COMMENT '{layer.capitalize()} layer'"
        for layer in config.curated_layers
    ]
    # Schemat techniczny "ops" i volume na checkpointy (schemat przed volume - rodzic przed dzieckiem).
    statements += [
        f"CREATE SCHEMA IF NOT EXISTS {catalog}.{OPS_SCHEMA} "
        "COMMENT 'Operational metadata: checkpoints, DQ results, run logs'",
        # Auto Loader trzyma tu stan strumienia (które pliki już przeczytał) i wywnioskowany schemat.
        f"CREATE VOLUME IF NOT EXISTS {catalog}.{OPS_SCHEMA}.{CHECKPOINTS_VOLUME} "
        "COMMENT 'Auto Loader checkpoints and schema locations'",
    ]
    # Wynik: 1 + len(source_systems) + len(curated_layers) + 2 poleceń (domyślnie 9).
    return statements


# Publiczne API modułu: z konfiguracji robi pełną, uporządkowaną listę poleceń SQL.
# envs=None oznacza "wszystkie środowiska z konfiguracji".
def build_statements(config: PlatformConfig, envs: Sequence[str] | None = None) -> list[str]:
    """Funkcja czysta: konfiguracja -> uporządkowany, idempotentny DDL. Rodzic zawsze przed dzieckiem."""
    # Funkcja czysta (pure function) = brak efektów ubocznych, ten sam input -> ten sam output; łatwa do testów.
    # Pusta lista lub None -> bierzemy wszystkie środowiska; w przeciwnym razie kopia jako krotka.
    selected_envs = tuple(envs) if envs else config.environments
    # Różnica zbiorów: środowiska podane przez użytkownika, których nie ma w konfiguracji.
    # sorted() daje stabilną, czytelną kolejność w komunikacie błędu.
    unknown = sorted(set(selected_envs) - set(config.environments))
    # Niepusta lista jest "prawdziwa" -> są nieznane środowiska.
    if unknown:
        # Fail fast, zanim jakikolwiek SQL zostanie wygenerowany/wykonany.
        raise ValueError(f"Unknown environments: {unknown}")

    # Katalog źródłowy zawsze jest pierwszy i zawsze jest tworzony (także przy --envs dev).
    statements = _sources_statements(config)
    # Następnie po kolei każde wybrane środowisko, w kolejności podanej przez użytkownika.
    for env in selected_envs:
        statements += _environment_statements(config, env)
    # Domyślnie: 6 + 9 * 2 = 24 polecenia.
    return statements


# Wykonuje polecenia. `execute` jest wstrzykiwany (dependency injection), więc ta funkcja
# nie wie nic o Sparku - w testach można podać np. lista.append.
def apply_statements(statements: Iterable[str], execute: Callable[[str], object]) -> int:
    """Wykonuje polecenia po kolei. `execute` to spark.sql na Databricks, a w testach atrapa."""
    # Licznik wykonanych poleceń - zwracany na końcu do logu podsumowującego.
    executed = 0
    # Ściśle sekwencyjnie: kolejność ma znaczenie (rodzic przed dzieckiem).
    for statement in statements:
        # Najpierw log, potem wykonanie - jeśli polecenie się wywali, w logu widać które.
        logger.info(statement)
        # Wynik (np. DataFrame ze spark.sql) jest ignorowany - DDL nic istotnego nie zwraca.
        # Wyjątek z execute przerywa pętlę; wcześniejsze polecenia zostają wykonane,
        # co jest bezpieczne, bo całość jest idempotentna i można po prostu puścić ponownie.
        execute(statement)
        # Zwiększamy licznik dopiero po udanym wykonaniu.
        executed += 1
    return executed


# Punkt wejścia CLI. argv=None -> argparse czyta sys.argv[1:]; w testach można podać listę.
def main(argv: Sequence[str] | None = None) -> None:
    # Parser z opisem widocznym w `--help`.
    parser = argparse.ArgumentParser(description="Idempotent Unity Catalog bootstrap")
    # nargs="+" -> jedna lub więcej wartości: --envs dev  albo  --envs dev prod.
    # Brak flagi -> args.envs == None -> wszystkie środowiska.
    parser.add_argument("--envs", nargs="+", help="Subset of environments, e.g. --envs dev")
    # store_true -> flaga bez wartości; obecna = True, brak = False.
    # argparse zamienia myślnik na podkreślnik: --dry-run -> args.dry_run.
    parser.add_argument("--dry-run", action="store_true", help="Print the SQL plan only")
    # type=Path -> argparse od razu zamienia podany napis na Path.
    # Domyślnie config/platform.yml obok tego modułu, więc w jobie flagi nie trzeba podawać.
    parser.add_argument(
        "--config", type=Path, default=DEFAULT_CONFIG_PATH,
        help=f"Path to the platform YAML config (default: {DEFAULT_CONFIG_PATH.name} next to this script)",
    )
    # Parsowanie; przy błędnych argumentach argparse sam wypisze błąd i zakończy (exit code 2).
    args = parser.parse_args(argv)

    # Wczytanie i walidacja YAML - błędny plik zatrzymuje skrypt, zanim powstanie jakikolwiek SQL.
    config = load_config(args.config)
    # Plan SQL budowany zawsze, także w trybie dry-run - więc walidacja (nazwy, środowiska)
    # działa lokalnie, bez Sparka.
    statements = build_statements(config, args.envs)
    # Tryb "na sucho": tylko wypisz plan i wyjdź.
    if args.dry_run:
        # Jedno polecenie na linię, na stdout (print, nie logger - bez timestampów, łatwo przekierować do pliku).
        print("\n".join(statements))
        # Wyjście przed importem pyspark - dry-run działa bez zainstalowanego Sparka.
        return

    # Konfiguracja logowania dopiero w trybie wykonania: poziom INFO, format z czasem i poziomem.
    # force=True usuwa wcześniej podpięte handlery (Databricks/IPython często już jakieś ma),
    # inaczej basicConfig byłby po cichu zignorowany i logi by się nie pokazały.
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", force=True)
    from pyspark.sql import SparkSession  # leniwy import: dry-run i testy jednostkowe nie potrzebują Sparka

    # Na Databricks zwraca istniejącą sesję (notebook/job już ją ma); lokalnie przez
    # Databricks Connect / rozszerzenie VS Code - sesję zdalną.
    spark = SparkSession.builder.getOrCreate()
    # Przekazujemy metodę spark.sql (bez wywołania!) jako funkcję wykonującą.
    executed = apply_statements(statements, spark.sql)
    # Podsumowanie; %d + argument zamiast f-stringa - formatowanie leniwe, robione tylko gdy log jest emitowany.
    logger.info("Done: %d statements executed", executed)


# Ten blok wykonuje się tylko przy uruchomieniu pliku jako skryptu (python uc_bootstrap.py),
# a nie przy imporcie (np. `from uc_bootstrap import build_statements` w testach).
if __name__ == "__main__":
    main()
