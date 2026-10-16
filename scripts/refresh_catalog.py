"""Régénère les instantanés du catalogue (`knowledge/catalog/*.json`) depuis les bases de leurs sources."""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from lib.knowledge_lint import catalog_path
from lib.query import CallerType, execute_autometa_tables_query, execute_metabase_query

ROOT = Path(__file__).parent.parent
# Why: les schémas autorisés par skills/autometa_tables_db/SKILL.md — l'agent ne lit pas les autres.
AUTOMETA_COLUMNS = """
SELECT table_schema || '.' || table_name, json_agg(column_name::text ORDER BY ordinal_position)::text
FROM information_schema.columns
WHERE table_schema IN ('public', 'monrecap', 'reporting', 'data_inclusion', 'esat', 'seeds', 'raw_dora', 'raw_rdvi',
                       'documentation')
GROUP BY table_schema, table_name
"""
METABASE_COLUMNS = """
SELECT table_schema || '.' || table_name, json_agg(column_name::text ORDER BY ordinal_position)::text
FROM information_schema.columns
WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
GROUP BY table_schema, table_name
"""
DOCUMENTED = "SELECT DISTINCT table_name FROM documentation.doc_autometa_tables"
CREDENTIALS = {"autometa_tables_db": "AUTOMETA_TABLES_DATABASE_URL", "metabase:dora": "METABASE_DORA_API_KEY"}


class Unreachable(Exception):
    pass


def query(source: str, sql: str) -> list[list]:
    if source == "autometa_tables_db":
        result = execute_autometa_tables_query(sql=sql, caller=CallerType.APP, timeout=300)
    else:
        result = execute_metabase_query(
            instance=source.removeprefix("metabase:"), caller=CallerType.APP, sql=sql, database_id=2, timeout=300
        )
    if not result.success:
        raise Unreachable(f"{source} injoignable : {result.error} — définir {CREDENTIALS[source]} dans .env")
    return result.data["rows"]


def documented_tables(source: str, previous: list[str]) -> list[str]:
    """Tables du dictionnaire de données ; sans dictionnaire, la liste de l'instantané précédent."""
    if source != "autometa_tables_db":
        return previous
    # Why: le dépôt est public et des noms d'archives Metabase contiennent des noms de personnes —
    # seules restent les archives déjà relues dans l'instantané précédent.
    return sorted(name for (name,) in query(source, DOCUMENTED) if "__mbarchiv__" not in name or name in previous)


def snapshot(source: str, previous: dict, today: date) -> dict:
    sql = AUTOMETA_COLUMNS if source == "autometa_tables_db" else METABASE_COLUMNS
    return {
        "source": catalog_path(ROOT, source).stem,
        "extracted_at": today.isoformat(),
        "documented_tables": documented_tables(source, previous.get("documented_tables", [])),
        "tables": dict(sorted((table, json.loads(columns)) for table, columns in query(source, sql))),
    }


def refresh(source: str, today: date) -> None:
    path = catalog_path(ROOT, source)
    previous = json.loads(path.read_text()) if path.is_file() else {}
    path.write_text(json.dumps(snapshot(source, previous, today), indent=1, ensure_ascii=False))
    print(f"{path.relative_to(ROOT)} régénéré")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sources", nargs="*", choices=sorted(CREDENTIALS), help="par défaut : toutes")
    failed = 0
    for source in parser.parse_args(argv).sources or sorted(CREDENTIALS):
        try:
            refresh(source, date.today())
        except Unreachable as error:
            print(f"{error} ; instantané existant conservé", file=sys.stderr)
            failed += 1
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
