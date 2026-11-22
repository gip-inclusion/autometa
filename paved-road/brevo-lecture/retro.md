# Rétro — 2026-11-22

Un premier essai réunissait Attio, Brevo et la skill `campagne_email` dans une seule branche, écrit avant tout contrat. En relisant `CONTRIBUTING.md` et `.claude/rules/review.md`, on l'a découpé en trois PR, chacune repartie de `main` avec son contrat validé et committé en premier, puis ses tests vus en échec avant le code. Le code de l'essai a servi de point de départ : le contrat date d'après lui, même si l'ordre des commits de la branche est conforme.

Ce qui a frotté :
- Le parcours tourne sous Windows sans `make` : les commandes de `scripts/paved_road_cli.py` ont été lancées directement, avec `PYTHONUTF8=1`, faute de quoi les fichiers markdown se lisent mal et le contrôle de la DoD ne trouve aucun critère. `paved_road_cli.py start` échoue aussi à la fin, sur l'installation des hooks par `make`, après avoir créé les dossiers.
- `make test` sous Windows : 121 échecs et 39 erreurs, identiques sur `main` (Postgres, Redis, `fcntl`, CLI absentes). La comparaison des listes d'échecs avec `main` a remplacé le vert. L'état du parcours est donc resté à `build`.
- La lentille a trouvé ce qu'aucun test n'avait prévu : une route d'Attio atteignable par un paramètre, l'objet rendu d'un modèle Brevo qui peut porter une donnée du destinataire, et une skill dont deux consignes se contredisaient. Deux passes ont suffi pour chaque branche.
