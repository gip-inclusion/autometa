from sqlalchemy import MetaData

from lib import dashboard_storage


def test_create_tables_creates_the_schema_then_the_tables(mocker):
    engine = mocker.patch("lib.dashboard_storage.get_engine").return_value
    create_all = mocker.patch("sqlalchemy.MetaData.create_all")

    dashboard_storage.create_tables(MetaData(schema="dashboard_storage"))

    statement = engine.begin.return_value.__enter__.return_value.execute.call_args.args[0]
    assert str(statement) == "CREATE SCHEMA IF NOT EXISTS dashboard_storage"
    create_all.assert_called_once_with(engine)
