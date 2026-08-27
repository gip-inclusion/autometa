# L6 — Fitness Functions

Origine et justifications : `docs/plans/2026-08-22-paved-road-workflow.md`, section « L6 —
Fitness Functions ».

Une fitness function est une règle exécutable qui mesure qu'un système préserve les propriétés
voulues à mesure qu'il change (Neal Ford, *Building Evolutionary Architectures*). C'est le versant
« vérificateur » des paires instruction / vérificateur : la prose de `.claude/rules/` reste, elle
n'est simplement plus seule à porter la règle.

## Ce qui est en place

**Règles de prose devenues règles ruff** (milestone 0) : `TID252` (imports relatifs parents),
`E722` (`except` nu), `S113` (appel HTTP sans timeout), `TID251` (imports et APIs bannis, dont
`os.getenv` / `os.environ` hors `web/config.py`). `S608` (SQL interpolé) et `BLE001` (`except
Exception`) restent **en observation** — comptés par `make lint`, sans bloquer.

Les exemptions `os.environ` se posent **en ligne**, avec un `# Why:`, jamais au fichier : une
exemption au fichier rendrait `web/cron.py` et `web/agents/cli.py` aveugles à une vraie lecture de
configuration ajoutée plus tard, précisément là où elle serait la plus délicate.

**Timeout au constructeur des clients de session** — `scripts/check_http_timeouts.py`. `S113` ne voit
qu'un appel littéral sans timeout ; un `httpx.Client()` construit sans timeout puis réutilisé lui
échappe, et c'est exactement la forme du dépôt. Le check refuse la construction sans `timeout=` ;
`lib/matomo.py`, `lib/metabase.py` et `lib/webinaires.py` en portent désormais un.

**Façade des tableaux de bord** — `lib/dashboard_api.py`. Voir ci-dessous.

**Protection des routes** — `scripts/check_route_auth.py`, baseline gelée dans `gates.toml`. Posée
dès le milestone 0 : le ratchet suppose qu'un premier incident soit rattrapable, or une exposition de
données de demandeurs d'emploi ne l'est pas.

## La façade des tableaux de bord

La cause racine n'est pas l'absence de détection, c'est le couplage : `data/interactive/` importait
`lib.query`, `web.db`, `web.config` — des internes qui n'ont jamais promis d'être stables. Un check
statique ne verrait que deux types de cassure sur sept ; il rate le comportement changé à signature
identique (dates en UTC au lieu de local, filtre appliqué par défaut, exception au lieu d'un `None`),
le contrat de `POST /api/query` que les tableaux de bord appellent en JS, et une colonne renommée
dans `dashboard_storage`. C'est cette ligne-là qui fait mal : le tableau de bord continue de tourner
et produit des chiffres faux, sans que rien ne se déclenche — `web/cron.py` ne remonte que les crashs.

D'où une façade explicite et versionnée, seul point d'entrée autorisé. On cesse de courir après les
cassures : on réduit la surface où elles peuvent se produire.

**Pas de graphe d'imports général** : quel seuil ? Un seuil arbitraire bloquerait du travail légitime
tout en laissant passer un renommage dévastateur à rayon nul.

**Le check ne peut pas vivre dans la CI.** `data/` n'est pas versionné — `git ls-files data/` ne
renvoie aucun fichier, la négation `!/data/interactive/` du `.gitignore` étant inerte, et les
artefacts vivent sur S3. Un check branché sur un diff s'exécuterait sur un dossier vide et serait
vert à perpétuité. Le contrôle s'applique donc aux deux moments où un tableau de bord passe
réellement :

- **À l'écriture** — `create_dashboard --adopt` et `update_dashboard` refusent un dossier dont un
  `.py` importe hors façade. Un archivage en est dispensé : retirer un tableau de bord hérité ne doit
  pas exiger de le migrer d'abord.
- **À l'exécution** — `web/cron.py` journalise et alerte sur le canal Slack existant, **en
  observation** : bloquer d'emblée casserait des tableaux de bord vivants. Les crons système ne sont
  pas concernés — ce sont des scripts de l'application, pas des tableaux de bord.

Les tests de la façade sont sa preuve : ils patchent `lib.query` en `autospec`, si bien qu'un
paramètre renommé en amont fait échouer la suite au lieu de casser silencieusement la production.

### Migration — à engager, pas encore engagée

Le design est explicite : le chantier ne s'engage pas sans savoir combien de tableaux de bord
tournent réellement. `python -m web.cron --facade-audit` donne ce nombre et la liste de ceux qui
restent à migrer. Il doit être lancé **en production** : la base de développement est vide, et la
migration elle-même est une opération sur S3, pas une PR.

Le passage de l'observation au blocage se décide sur ce chiffre, une fois la liste vide.

## En réserve

Migrations destructives et dérive `knowledge/` — écrits quand le friction log les réclame. Ce
milestone n'a pas de fin : c'est le régime permanent, une fitness function à la fois.
