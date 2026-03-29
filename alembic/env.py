"""Alembic environment — reads DATABASE_URL from web.config, uses web.models metadata."""

from sqlalchemy import create_engine

from alembic import context
from web import config
from web.models import Base

target_metadata = Base.metadata


EXCLUDE_TABLES = {
    "spatial_ref_sys",
    "topology",
    "layer",
    "state",
    "county",
    "place",
    "faces",
    "edges",
    "addr",
    "zip_lookup",
    "zip_lookup_all",
    "zip_lookup_base",
    "zip_state",
    "zip_state_loc",
    "geocode_settings",
    "geocode_settings_default",
    "direction_lookup",
    "secondary_unit_lookup",
    "state_lookup",
    "street_type_lookup",
    "countysub_lookup",
    "county_lookup",
    "place_lookup",
    "loader_platform",
    "loader_variables",
    "loader_lookuptables",
    "tabblock",
    "tabblock20",
    "tract",
    "bg",
    "featnames",
    "zcta5",
    "cousub",
    "addrfeat",
    "pagc_gaz",
    "pagc_lex",
    "pagc_rules",
}


def include_object(obj, name, type_, reflected, compare_to):
    if type_ == "table" and name in EXCLUDE_TABLES:
        return False
    return True


def run_migrations_online():
    engine = create_engine(config.DATABASE_URL)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, include_object=include_object)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
