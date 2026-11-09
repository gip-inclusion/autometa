# C10 — Fraîcheur et capacité

> Vague 2 · dépend de C2 et de D6 · constats F26, F28, F13 · établit I3 (fraîcheur) et I12 · zone
> critique `cron.json` (taille du conteneur) · migration : oui (délai de fraîcheur), à fusionner
> après C3 (K10).

## Pourquoi

- **F26** : une vingtaine de TDB échouent chaque jour, et 15 à chaque run. L'alerte n'est envoyée
  qu'une fois, au premier échec, dans le canal commun, et jamais à l'auteur. « Le script s'est
  terminé sans erreur » ne dit pas si la donnée affichée est récente.
- **F28** : depuis #236, le lot `tableaux-internes` a un budget de 3 600 s. Mesuré : 2 528 à
  3 225 s (le 05/10), soit environ 10 % de marge. Au-delà, des TDB passent en `skipped`. Le lot
  tourne toujours dans le conteneur M (512 Mo), qui était tué faute de mémoire.
- **F13** : exécution série. À 500 TDB, environ 4 h de lot.

## Brief pour `/paved-road:paved-road`

> Chaque tableau de bord doit afficher depuis quand ses données datent, et me prévenir, moi son
> auteur, quand elles sont trop vieilles. Les tableaux de bord qui échouent depuis longtemps doivent
> m'être proposés à l'archivage. Les rafraîchissements du matin doivent tenir dans leur créneau,
> même avec beaucoup plus de tableaux de bord.

## DoD proposée

DOD-1 — Quand la donnée d'un tableau de bord a dépassé son délai de fraîcheur (2 jours par défaut
  pour un tableau de bord quotidien), son auteur reçoit une notification, une fois par épisode.

DOD-2 — Une page de tableau de bord publiée dont la donnée a dépassé son délai affiche un bandeau
  « Données du JJ/MM/AAAA ».

DOD-3 — La liste des tableaux de bord permet de filtrer ceux dont la donnée est périmée, avec leur
  âge.

DOD-4 — Un tableau de bord en échec depuis 14 jours est proposé à l'archivage à son auteur.

DOD-5 — Avec le parc actuel, les rafraîchissements du matin se terminent avant la moitié du budget,
  et la marge restante est affichée sur `/cron`.

DOD-6 — Quand la marge passe sous 25 %, une alerte part.

## Solution recommandée

- **Âge de la donnée** : `metadata.generated_at` du `data.json` (convention déjà documentée),
  sinon la date du dernier succès. Calculé après chaque run et stocké
  (`dashboards.data_generated_at`). Délai par cadence : 2 j quotidien, 9 j hebdomadaire, 35 j
  mensuel ; surcharge possible par TDB.
- **Notification à l'auteur** : `first_author_email`, par le canal existant (e-mail ou Slack). Une
  fois par épisode, avec un rappel hebdomadaire.
- **Bandeau public** : injecté par l'artefact (C3 ou C4) quand la publication est `stale-code` ou
  périmée. Petit script commun, pas une modification de chaque TDB.
- **Parallélisme (D6)** : `run_all` exécute les tâches TDB avec un `ThreadPoolExecutor` de N
  workers (N configurable, 4 par défaut). Chaque tâche reste un sous-processus avec son timeout.
  `record_run` et l'enregistrement du lot sont thread-safe (une session par tâche). Le conteneur
  `tableaux-internes` passe en L dans `cron.json`.
- Budget recalculé à partir de la mesure.

## Fichiers

- `web/cron.py` : `run_all`, `execute_task` (âge de la donnée), `close_batch_run` (marge).
- `web/models.py` + migration : `data_generated_at`, délai.
- `cron.json` (zone critique) : taille du lot.
- `web/routes/dashboards.py`, `web/templates/dashboards.html`, `web/templates/cron.html`.

## Tests rouges

Nouveaux : run parallèle de N tâches (toutes enregistrées, aucune perdue en cas d'exception) ;
notification unique par épisode ; bandeau quand la donnée a dépassé son délai.

## Cohérence

- K9 : N workers × connexions (C7) × mémoire (taille du conteneur).
- K10 : migration après C3.
- K1 : affiche le statut `stale-code` produit par C4.

## Prompt de lancement

> Lis `docs/plans/2026-10-06-tdb/README.md` (§ 1 D6, § 4.2 K1, K9 et K10) puis
> `docs/plans/2026-10-06-tdb/C10-fraicheur-capacite.md`. Vérifie que C2 est fusionné, et que C3
> l'est avant de fusionner ta migration. Lance le parcours paved road sur la branche
> `<auteur>/feat/tdb-c10-fraicheur-capacite`. Reprends la DoD proposée comme base d'Align et fais-la
> valider avant de coder. `cron.json` est en zone critique. Si une hypothèse est fausse,
> arrête-toi et remonte la question.
