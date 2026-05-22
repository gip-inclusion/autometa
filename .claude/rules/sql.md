ORM : utiliser SQLAlchemy 2.0 (style `select()`, `session.scalars()`) pour toutes les requêtes. Les modèles sont dans `web/models.py` — c'est la source de vérité pour le schéma. Ne jamais écrire de raw SQL sauf quand c'est clairement plus concis (agrégations complexes, TRUNCATE, full-text search). Le raw SQL doit utiliser `text()` avec des paramètres nommés (`:param`), jamais `%s`.

Migrations : Alembic uniquement. Toute modification du schéma doit :
1. Modifier le modèle dans `web/models.py`
2. Générer la migration : `alembic revision --autogenerate -m "description"`
3. Vérifier la migration générée (Alembic peut manquer des index ou des contraintes)
4. Appliquer : `alembic upgrade head` (fait automatiquement au post-deploy sur Scalingo)

Ne jamais modifier les tables directement en SQL. Ne jamais écrire de migration manuelle sauf pour des opérations non-DDL (data migration, backfill).

`make ci` exécute `alembic check` (cible `check-migrations`) : la CI échoue si `web/models.py` diverge de la dernière migration. Suppose une DB locale à jour (`make migrate` au préalable).

Ne jamais interpoler de valeurs dans le SQL. Toujours utiliser des paramètres nommés ou l'ORM.
