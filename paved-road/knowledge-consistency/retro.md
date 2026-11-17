# Rétro — knowledge-consistency

Le parcours a été coupé en deux par l'orchestrateur : une phase d'investigation et de conception,
soumise au demandeur, puis l'implémentation après son feu vert. Conséquence assumée : la lentille
`gap-hunter` n'a pas tourné avant la validation, qui portait sur une direction et cinq décisions
déjà rédigées. DOD-9 a été ajouté au moment de committer le contrat, tiré mot pour mot du brief de
validation ; la section « Validation » le dit.

Ce qui a frotté :

- **Le vérificateur a été écrit avant ses tests**, comme un sondage pour mesurer ce que le dépôt
  contenait de faux avant de rédiger les critères de preuve. Pour que les rouges restent honnêtes,
  le module a été mis de côté le temps de journaliser les rouges de DOD-1 à DOD-4 et DOD-9 (échec à
  l'import) ; ceux de DOD-5 à DOD-8 ont échoué sur le contenu réel du dépôt, module présent. Un
  parcours mené d'une traite aurait écrit les tests d'abord.
- **Deux assertions ont changé après leur rouge**, avant tout commit : DOD-6 exigeait que la fiche
  des actes métier ne nomme plus `int_iMER` — or elle documente un script de tableau de bord qui
  l'utilise réellement ; effacer la mention aurait rendu la fiche fausse. Le test exige désormais
  qu'elle signale l'écart et le double compte. DOD-7 cherchait l'ordre des rangs dans toute la
  section au lieu de la liste numérotée.
- **Les empreintes de preuve ne couvrent pas `knowledge/` ni `AGENT.md`** (`web`, `lib`, `scripts`,
  `skills`, `alembic`, `tests` seulement). Une attestation de DOD-5, DOD-6 ou DOD-8 ne périme donc
  pas quand la fiche qu'elle prouve change. Le test tourne dans `make test` à chaque PR, ce qui
  compense pour la suite, mais l'attestation elle-même ment par omission. Friction à porter au
  parcours : ajouter `knowledge` et `AGENT.md` au périmètre empreinté — modification de
  `lib/attestation.py`, interdite à l'agent.
- **Le hook `pre-commit` d'un worktree neuf échoue** (« `pre-commit` not found ») tant que
  `.venv/bin` n'est pas dans le `PATH` ; `make paved-road-start` installe le hook mais pas ce chemin.
- **La lentille a trouvé trois vrais bloqueurs**, dont un que l'agent avait lui-même créé : corriger
  deux adresses dans le tableau des sites sans contrôle d'adresse laissait deux fiches les
  contredire. C'est exactement la récidive que le dispositif veut empêcher, et la meilleure
  justification de la lentille.

Ce qui a surpris : `AGENT.md`, le seul fichier injecté verbatim, était la copie la plus ancienne et
la plus fausse des règles (branches `master`, deux URL qui ne résolvent plus, règle de priorité
incomplète). Le fichier le plus lu était le moins relu.

Limites laissées ouvertes, écrites dans la PR : paraphrase courte d'une règle (lentille
`knowledge-drift`), fonction citée en prose, tables citées hors bloc SQL, contrôle des tables en
attente des instantanés du catalogue (PR suivante).

## Intégration des instantanés du catalogue — 2026-10-13

Les deux instantanés extraits en production (`autometa_tables_db`, `metabase_dora`) sont versionnés.
Confronté au vrai catalogue, le contrôle a dû changer trois choses, chacune rougie avant d'être
corrigée : la comparaison se fait casse comprise (`int_iMER`, `monrecap.Contacts` existent tels
quels ; replier la casse produisait de fausses alertes sur les tables de référence) ; les tables
documentées mais absentes de l'instantané (archives Metabase, `int_`, `_v0`) sont invérifiables et
sautées ; les commentaires SQL et `information_schema` ne sont plus lus comme des tables. Il a trouvé
deux vraies références mortes dans la fiche Dora, toutes deux corrigées. Limite : un identifiant en
casse mixte écrit sans guillemets dans un bloc SQL passe le contrôle alors que PostgreSQL le replie
en minuscules — aucun cas dans le dépôt aujourd'hui.
