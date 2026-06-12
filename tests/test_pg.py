from sqlalchemy.pool import NullPool

import lib.pg as pg


def test_build_engine_nullpool_and_timeout(mocker):
    mock_create = mocker.patch("lib.pg.create_engine")

    pg.build_engine("postgresql://u:p@db/x", 60)

    mock_create.assert_called_once_with(
        "postgresql://u:p@db/x",
        poolclass=NullPool,
        connect_args={"options": "-c statement_timeout=60000"},
    )
