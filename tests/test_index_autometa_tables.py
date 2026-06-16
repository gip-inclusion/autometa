import importlib.util
from pathlib import Path

import pytest
from sqlalchemy.exc import SQLAlchemyError

spec = importlib.util.spec_from_file_location(
    "index_autometa_tables_cron",
    Path(__file__).resolve().parent.parent / "cron" / "index-autometa-tables" / "cron.py",
)
cron = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cron)

TOTAL_STATEMENTS = sum(len(columns_list) + 1 for columns_list in cron.INDEXES.values())


def make_engine(mocker, execute=None):
    conn = mocker.MagicMock()
    if execute is not None:
        conn.execute.side_effect = execute
    engine = mocker.MagicMock()
    engine.connect.return_value.__enter__.return_value = conn
    return engine, conn


@pytest.mark.parametrize(
    ("schema", "table", "columns_list", "expected"),
    [
        (
            "les_emplois",
            "candidats",
            [("id",), ("département",)],
            [
                'CREATE INDEX IF NOT EXISTS "idx_candidats_id" ON "les_emplois"."candidats" ("id")',
                'CREATE INDEX IF NOT EXISTS "idx_candidats_département" ON "les_emplois"."candidats" ("département")',
                'ANALYZE "les_emplois"."candidats"',
            ],
        ),
        (
            "dora",
            "services_service_categories",
            [("service_id", "servicecategory_id")],
            [
                'CREATE INDEX IF NOT EXISTS "idx_services_service_categories_service_id_servicecategory_id" '
                'ON "dora"."services_service_categories" ("service_id", "servicecategory_id")',
                'ANALYZE "dora"."services_service_categories"',
            ],
        ),
    ],
)
def test_table_statements(schema, table, columns_list, expected):
    assert cron.table_statements(schema, table, columns_list) == expected


def test_index_name_truncated_to_63_chars():
    statements = cron.table_statements("s", "a" * 80, [("col",)])
    name = statements[0].split('"')[1]
    assert name == ("idx_" + "a" * 80 + "_col")[:63]


def test_main_skips_without_database_url(mocker):
    mocker.patch.object(cron.config, "AUTOMETA_TABLES_DATABASE_URL", "")
    create_engine = mocker.patch.object(cron, "create_engine")

    cron.main()

    create_engine.assert_not_called()


def test_main_executes_all_statements(mocker):
    mocker.patch.object(cron.config, "AUTOMETA_TABLES_DATABASE_URL", "postgresql://example")
    engine, conn = make_engine(mocker)
    mocker.patch.object(cron, "create_engine", return_value=engine)

    cron.main()

    assert conn.execute.call_count == TOTAL_STATEMENTS


def test_main_continues_after_failures_then_raises(mocker):
    mocker.patch.object(cron.config, "AUTOMETA_TABLES_DATABASE_URL", "postgresql://example")

    def execute(clause):
        if '"candidats"' in str(clause) and "CREATE INDEX" in str(clause):
            raise SQLAlchemyError("boom")

    engine, conn = make_engine(mocker, execute)
    mocker.patch.object(cron, "create_engine", return_value=engine)

    with pytest.raises(RuntimeError, match="2 statements failed"):
        cron.main()

    assert conn.execute.call_count == TOTAL_STATEMENTS
