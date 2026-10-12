# Des connaissances qui ne se contredisent plus

## Ce que je veux

Qu'Autometa ne réponde plus différemment à la même question selon la fiche qu'il a lue en premier.
Les fiches de connaissance fausses ou périmées (comme le bouton « Je suis intéressé » de Dora, qui
n'existe pas) doivent être corrigées, et surtout une contradiction ne doit plus pouvoir revenir sans
que quelqu'un s'en aperçoive avant la mise en production.

## Ce qui devra marcher

DOD-1 — [du brief : « ne pas laisser les infos contradictoires créer des comportements aléatoires »]
  Quand une fiche de connaissance, un skill ou les consignes d'Autometa citent un fichier, un module
  ou une fonction du dépôt qui n'existe pas, la vérification automatique de la PR échoue et nomme la
  fiche, la ligne et la référence introuvable.

DOD-2 — [du brief : « un moyen plus générique »] Le numéro, le nom et l'adresse de chaque site
  suivi dans Matomo n'ont qu'une seule référence : le tableau des sites des consignes d'Autometa.
  Quand une fiche, un skill ou la configuration donnent pour un site un numéro, un nom ou un
  conteneur différent, ou citent une instance Metabase qui n'existe pas, la vérification de la PR
  échoue et nomme les deux valeurs.

DOD-3 — [du brief : « ne pas laisser les infos contradictoires »] Chaque fiche de connaissance
  déclare la source de données qu'elle décrit et la date de sa dernière vérification. Une fiche qui
  ne le déclare pas, ou qui déclare une source inconnue, fait échouer la vérification. Une fiche
  vérifiée il y a plus de 180 jours est signalée, sans bloquer.

DOD-4 — [du brief : « les recommandations knowledge peuvent entrer en contradiction avec celles de
  skills/autometa_tables »] Les règles qui disent quelle source de données utiliser en priorité
  n'existent qu'à un seul endroit, les consignes de production d'Autometa ; les règles de choix des
  tables de la base centrale n'existent que dans son skill. Les autres documents y renvoient. Quand
  une PR recopie une de ces règles ailleurs, la vérification échoue et nomme les deux endroits.

DOD-5 — [du brief : « le bouton "je suis intéressé" n'existe pas »] La fiche Dora ne parle plus de
  bouton « Je suis intéressé » : elle décrit ce qui enregistre réellement une mobilisation dans Dora
  (orienter un bénéficiaire, afficher les coordonnées d'un service, suivre un lien de mobilisation
  externe), en citant le code Dora qui le montre. Une affirmation reconnue fausse ne peut plus
  réapparaître dans une fiche sans faire échouer la vérification.

DOD-6 — [du brief : « récupérer les incohérences de knowledge/dora/README.md »] Pour une question
  sur Dora, la fiche Dora et le skill de la base centrale donnent la même route : les tables de
  référence Dora d'abord, le calcul à la main sur le Metabase Dora seulement en repli annoncé. La
  fiche Dora et la fiche des actes métier donnent la même définition de l'iMER, ou renvoient l'une à
  l'autre ; ce qu'aucune lecture n'a pu établir sans la base (le périmètre exact de la table de
  référence) est écrit comme « à confirmer », pas deviné.

DOD-7 — [du brief : « ne pas laisser les infos contradictoires créer des comportements aléatoires »]
  Quand Autometa rencontre malgré tout deux consignes qui divergent, il applique un ordre de priorité
  écrit dans ses consignes (catalogue réel des bases, puis skill de la source, puis fiche de
  connaissance) et le signale dans sa réponse au lieu de choisir en silence.
  Ce critère décrit un comportement du modèle : il ne se démontre pas par un test automatique. Sa
  preuve sera la présence de la règle, à un seul endroit, dans les consignes.

DOD-8 — [du brief : « récupérer les incohérences »] Les autres incohérences relevées dans
  l'investigation (numéros de site Matomo, branches des dépôts GitHub, statuts d'orientation Dora,
  versions de tables de référence, chemins et imports morts, consignes Matomo opposées, instance
  Metabase oubliée) sont corrigées, ou listées dans la PR avec la raison pour laquelle elles ne le
  sont pas.

DOD-9 — [du brief de phase 2 : « une doc knowledge/skill ne peut plus référencer une table/colonne
  inexistante », « valider contre un snapshot de catalogue committé »] Quand une fiche cite une
  table, ou une colonne d'une table, absente du catalogue des tables réelles de sa source (un
  instantané versionné dans le dépôt), la vérification échoue et nomme la fiche, la ligne et la
  table ou la colonne. Tant que l'instantané d'une source n'est pas versionné, la vérification le
  signale et ne contrôle pas les tables de cette source.

## Sources lues

- `web/agents/base.py`, `web/agents/cli.py`, `AGENT.md`, `CLAUDE.md`, `skills/autometa_tables_db/SKILL.md`,
  `knowledge/**`, `tests/test_sources_registry.py`, `web/routes/knowledge.py` — **R1** : seul
  `AGENT.md` est injecté verbatim ; les fiches knowledge ne sont listées que par leur chemin ; aucun
  contrôle ne lit leur contenu ; l'édition de knowledge depuis l'appli est désactivée, la PR est le
  seul chemin d'écriture. D'où des critères vérifiés à la PR (DOD-1 à DOD-4, DOD-9).
- `gip-inclusion/dora` @ `6e82bc9` (2026-10-12) : `back/dora/stats/models.py:330`,
  `front/src/lib/utils/stats.ts:77`, `front/src/routes/(modeles-services)/components/service-body/service-body.svelte:87`,
  `front/src/routes/(modeles-services)/services/[slug]/orienter/contact-info.svelte:24`,
  `back/dora/orientations/models.py:34` — **R1** : aucun bouton « Je suis intéressé » ; statuts
  d'orientation accentués (DOD-5, DOD-8).
- API GitHub publique, `default_branch` de `les-emplois`, `le-marche`, `dora` : `main` (DOD-8).
- PR #224 et #227 — **R5** : #224 a ajouté la règle `fct_dora__*` sans toucher la fiche Dora
  (origine de DOD-6) ; #227 traite l'accès aux sources, pas la cohérence des consignes.
- `docs/paved-road/l5-design-coherence.md:32`, `docs/paved-road/l6-fitness-functions.md:82`,
  `docs/plans/2026-08-22-paved-road-workflow.md:223,242` — **R5** : « dérive knowledge » et lentille
  `knowledge-drift` prévues « sur incident » ; un vérificateur LLM n'est jamais un gate (d'où DOD-7
  hors test).
- `knowledge/bizdev/glossaire.md` — **R3** : iMER, orientation, acte métier.
- `config/sources.yaml` — **R1** : instances Metabase et conteneurs Matomo existants (DOD-2).
- Seuil de 180 jours (DOD-3) — **R2** : aucune mesure source ; proposition soumise en décision 4 et
  acceptée telle quelle.

Pas de tableau de bord touché : **R4** ne se déclenche pas. **R6** : non consulté — pas d'accès aux
conversations de production depuis la machine de développement.

## Questions ouvertes

Aucune. Le contenu réel des tables (périmètre de `fct_dora__imer`, valeurs de statut stockées dans
la base analytique Dora) n'est pas une question ouverte du contrat : DOD-6 et DOD-9 disent comment
il est traité tant que le catalogue n'est pas versionné.

## Validation

Validé par Alexis Akinyemi le 2026-10-12.

Validation relayée par l'orchestrateur de session (« feu vert sur la direction, les cinq décisions
= défauts acceptés »). Cinq décisions soumises, cinq défauts retenus : corrections, vérification et
ordre de priorité dans cette PR, comparaison nocturne avec les bases dans une PR suivante ;
vérification dans la suite de tests existante ; règles de choix des sources uniquement dans les
consignes de production ; fiche de plus de 180 jours signalée sans bloquer ; calcul de l'iMER à la
main conservé comme repli. DOD-9 vient du brief de validation lui-même (contrôle des tables contre
un instantané versionné du catalogue).
