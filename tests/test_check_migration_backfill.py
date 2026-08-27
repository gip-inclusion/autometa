import importlib.util
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    "check_migration_backfill", Path(__file__).parent.parent / "scripts" / "check_migration_backfill.py"
)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def migration(corps: str) -> str:
    return f"def upgrade() -> None:\n{corps}"


ALTER_SANS_BACKFILL = migration('    op.alter_column("reports", "version", nullable=False)\n')
ALTER_AVEC_BACKFILL = migration(
    '    op.execute(remplissage)\n    op.alter_column("reports", "version", nullable=False)\n'
)
ALTER_APRES_COUP = migration('    op.alter_column("reports", "version", nullable=False)\n    op.execute(remplissage)\n')
ALTER_NULLABLE = migration('    op.alter_column("reports", "version", nullable=True)\n')
AJOUT_NON_NUL = migration('    op.add_column("reports", sa.Column("titre", sa.String(), nullable=False))\n')
AJOUT_AVEC_DEFAUT = migration(
    '    op.add_column("reports", sa.Column("titre", sa.String(), nullable=False, server_default=""))\n'
)
AJOUT_NULLABLE = migration('    op.add_column("reports", sa.Column("titre", sa.String(), nullable=True))\n')
SANS_UPGRADE = 'def downgrade() -> None:\n    op.alter_column("reports", "version", nullable=False)\n'


@pytest.mark.parametrize(
    ("source", "attendu"),
    [
        (ALTER_SANS_BACKFILL, ["reports.version"]),
        (ALTER_AVEC_BACKFILL, []),
        (ALTER_APRES_COUP, ["reports.version"]),
        (ALTER_NULLABLE, []),
        (AJOUT_NON_NUL, ["reports.?"]),
        (AJOUT_AVEC_DEFAUT, []),
        (AJOUT_NULLABLE, []),
        (SANS_UPGRADE, []),
    ],
)
def test_signale_les_contraintes_non_nulles_sans_backfill(source, attendu):
    assert _module.unbackfilled_columns(source) == attendu


def test_reproduit_l_incident_de_juin_2026():
    """La migration `b12cbac64ff9` a dû se voir ajouter sept remplissages avant ses alter_column."""
    incident = Path("alembic/versions/b12cbac64ff9_enforce_not_null_on_default_backed_.py").read_text()

    assert _module.unbackfilled_columns(incident) == []
    assert len(_module.unbackfilled_columns(incident.replace("op.execute", "noop"))) == 7


def test_les_migrations_du_depot_sont_toutes_couvertes():
    signalees = [
        chemin.name for chemin in _module.VERSIONS.glob("*.py") if _module.unbackfilled_columns(chemin.read_text())
    ]

    assert signalees == []


def test_main_est_vert_quand_aucune_migration_ne_signale_rien(capsys):
    assert _module.main() == 0
    assert "aucune contrainte non nulle sans backfill" in capsys.readouterr().out


def test_main_echoue_et_dit_quoi_faire(tmp_path, monkeypatch, capsys):
    (tmp_path / "0001_ajout.py").write_text(ALTER_SANS_BACKFILL)
    monkeypatch.setattr(_module, "VERSIONS", tmp_path)

    assert _module.main() == 1
    sortie = capsys.readouterr().out
    assert "0001_ajout.py — reports.version" in sortie
    assert "échoue en production sur les lignes déjà présentes" in sortie
