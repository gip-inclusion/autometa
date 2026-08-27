# L1 — Attestation

Ce document fixe ce qu'est une attestation, ce qui la périme, et les quatre commandes du parcours.
Il ne décrit pas l'implémentation : `lib/attestation.py` et `scripts/paved_road_cli.py` en sont la
référence.

Origine et justifications : `docs/plans/2026-08-22-paved-road-workflow.md`, section « L1 —
Attestation ».

## Ce que L1 garantit, et ce qu'il ne garantit pas

**Plus aucun verdict sans code de sortie 0.** L'état ne progresse que si de vraies commandes
sortent en 0, et le verdict vient du code de sortie, jamais d'une phrase de l'agent.

L'emprunt à SLSA / in-toto est partiel, et il faut le dire : le rattachement au contenu prouvé
traite la **péremption**, pas la **fabrication**. Un fichier écrit à la main porte les bonnes
empreintes. Ce que L1 garantit est donc plus étroit que ce que le mot « attestation » suggère —
l'evidence comportementale reste déclarative jusqu'à L3, où elle devient la sortie d'un test
rejouable.

La CI ne fait pas confiance à ces attestations : le job « Ce qui devait marcher » **rejoue** les
checks et compare son résultat au verdict journalisé. Le journal est un cache et une source de
statistiques, jamais une autorité.

## Quatre commandes, trois états

Aucune CLI propriétaire : des cibles du `Makefile`, invocables par un agent, par un humain ou par
la CI. `FEATURE=<slug>` surcharge le répertoire d'artefacts, déduit sinon de la branche courante.

| Commande | Rôle |
|---|---|
| `make paved-road-start` | Ouvre `paved-road/<slug>/` et le gabarit de definition of done |
| `make paved-road-status` | État atteint, verdict de chaque critère, compteur d'échecs réparables |
| `make paved-road-checks` | Lance les checks de l'état courant, sans rien journaliser |
| `make paved-road-advance` | Prouve un critère, ou fait progresser l'état |

Les états sont les trois temps du parcours : `align`, `build`, `prove`. `advance` lance les checks
de l'état courant et ne progresse que s'ils sortent tous en 0.

Pour démontrer un critère :

```
make paved-road-advance DOD=DOD-1 CMD='uv run --frozen pytest tests/test_rapports.py -k "…" -q'
```

`PATHS="web lib data/interactive/mon-tdb"` fixe les chemins prouvés — par défaut `web`, `lib`,
`scripts`, `alembic` et `tests`. Un chemin peut être un répertoire comme un fichier : plus il est
large, plus une modification sans rapport périme la preuve et impose de la rejouer.

## Rattachement au code : le contenu prouvé, ni la date ni le commit

Une date de fichier n'est pas une attestation : l'agent dispose de Bash, et `touch` rend n'importe
quelle preuve « fraîche ». Le SHA de HEAD ne convient pas davantage — l'attestation est committée
par construction, et ce commit déplace HEAD ; re-prouver produirait un nouveau commit, donc une
nouvelle invalidation, et la boucle ne terminerait pas. S'y ajoute le rebase, obligatoire ici, qui
réécrit tous les SHA d'une branche dont le code n'a pas bougé d'une ligne.

Chaque attestation enregistre donc les **empreintes d'arbre git** des chemins qu'elle prouve, **à
l'exclusion du répertoire `paved-road/`** — attestations et journal compris. Sans cette exclusion,
on reproduit la boucle.

Conséquences : ranger la preuve et rebaser sont neutres, une vraie modification du code invalide
toujours, et l'attestation reste vérifiable par quiconque sans faire confiance à l'horloge.

`advance` refuse de prouver un chemin portant des modifications non committées : l'empreinte du
HEAD ne décrirait pas ce que la commande a réellement exécuté.

## Une attestation par critère

Chaque `DOD-N` porte la sienne, sous `paved-road/<slug>/attestations/DOD-N.md` : le critère, la
commande lancée, son code de sortie, la sortie tronquée, les empreintes, et un verdict démontré /
non démontré. Un critère non démontré ne peut donc pas se noyer dans un rapport global.

Le récapitulatif en français n'est pas dupliqué là : il est produit par la description de PR.

## Ce qu'une attestation ne contient jamais

**Le dépôt est public**, et le produit manipule des données sur des demandeurs d'emploi.

> Sous `attestations/`, uniquement ce qu'`advance` produit seul : commande, code de sortie, sortie
> tronquée, empreintes, verdict. Aucune image, aucun binaire, aucune sortie brute de requête.

Un check le refuse, **directement bloquant** : le faux positif coûte un renommage de chemin, le
faux négatif est irréversible dans un historique public. `gitleaks` ne protège pas de cela — il
cherche des motifs de secrets, pas des noms de personnes, et n'ouvre pas une image.

Les captures produites en L4 transiteront par les artefacts de CI ou un commentaire de PR, hors
dépôt. Le champ narratif « ce qui a été observé » n'existe pas dans l'attestation : il appartient
au friction log, qui n'a ni la même autorité ni la même durée de vie.

## Le journal est un répertoire

`paved-road/<slug>/journal/` porte un fichier par événement, nommé par horodatage et empreinte
courte, agrégé à la lecture. Il est committé — la CI porte les guardrails et ne verrait pas un
fichier ignoré.

Sur un journal mono-fichier, résoudre un conflit de rebase serait une écriture manuelle par
l'agent, hors `advance` et sans code de sortie : exactement l'invariant dont L1 tire son autorité.
Avec un répertoire, git ne conflicte jamais sur des fichiers distincts et le rebase devient inerte.

**Seul `advance` y écrit**, et seulement d'après des codes de sortie réels.

## Échecs : tri par famille, pas compteur

Chaque check déclare la famille de son échec, et c'est elle qui commande la suite.

| Famille | Causes | Réponse |
|---|---|---|
| **A. Réparable** | test rouge, lint, couverture, attestation invalidée, rebase à faire | L'agent réessaie — travail normal |
| **B. Environnement** | Postgres ou Redis absent, Matomo ou Metabase indisponible, réseau | Arrêt immédiat, signalé comme panne |
| **C. Question métier** | critère ambigu, infaisable, périmètre flou | Retour au citizen developer |
| **D. Interdit** | abaisser un seuil, migration destructive, suppression de test, contenu proscrit sous `attestations/` | Break-glass |

Réessayer sur A est légitime et fréquent ; réessayer sur B, C ou D est une erreur dès la première
fois.

### Plafond de la famille A — en observation

`advance` journalise le nombre d'échecs de famille A enchaînés depuis le dernier succès, **sans
agir**. La valeur du plafond sera choisie sur les données du milestone 1, pas devinée. Quand il
sera actif, il produira une **conversion en HITL checkpoint**, pas un échec : l'agent se met en
pause, il ne se débloque jamais lui-même.

## Dette assumée

L'antériorité de la DoD (« le premier commit de la branche est celui qui l'ajoute ») reste une
règle de revue, non un check. Sur une pile de branches, la base de comparaison n'est pas
déterminable de façon fiable, et un contrôle qui crie à tort sur le cas nominal cesse d'être lu.

## Les preuves qui ne se rejouent pas

Deux formes échappent au rejeu, parce que le job requis n'a ni navigateur, ni application servie,
ni les accès du nightly :

- une preuve jouée dans le navigateur (`pytest browser/…`, ou `-m browser`) porte le verdict
  **`démontré (E2E)`** ;
- une mesure faite en nightly (`--nightly`) porte **`démontré (nightly)`**.

Le verdict porte la mention, et `check_paved_road.py` la lit pour passer son tour. Sans cela, une
PR deviendrait infusionnable dès que le check est requis : la commande échouerait dans le job, non
parce que la preuve est fausse, mais parce que le job ne sait pas la rejouer.

Le contrat doit annoncer cette forme **d'avance**. Une preuve non rejouable décidée après coup est
une preuve qu'on a renoncé à vérifier.
