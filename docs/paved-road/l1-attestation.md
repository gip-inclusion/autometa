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

Rien ne rejoue ces attestations : la CI ne lit aucun artefact du parcours, et ce choix est motivé
plus bas. Ce qui les tient, c'est que l'empreinte du contenu prouvé les périme dès que le code
change, et que seul `advance` y écrit. Le journal reste un cache et une source de statistiques,
jamais une autorité.

## Quatre commandes, trois états

Aucune CLI propriétaire : des cibles du `Makefile`, invocables par un agent, par un humain ou par
la CI. `FEATURE=<slug>` surcharge le répertoire d'artefacts, déduit sinon de la branche courante.

| Commande | Rôle |
|---|---|
| `make paved-road-start` | Ouvre `paved-road/<slug>/` et le gabarit de definition of done |
| `make paved-road-status` | État atteint, verdict de chaque critère, compteur d'échecs réparables |
| `make paved-road-checks` | Lance les checks de l'état courant, sans rien journaliser |
| `make paved-road-advance` | Journalise un rouge, prouve un critère, ou fait progresser l'état |

Les états sont les trois temps du parcours : `align`, `build`, `prove`. `advance` lance les checks
de l'état courant et ne progresse que s'ils sortent tous en 0.

Pour démontrer un critère, le rouge d'abord, le vert ensuite :

```
make paved-road-advance DOD=DOD-1 RED=1 CMD='uv run --frozen pytest tests/test_rapports.py -k dod_1'
make paved-road-advance DOD=DOD-1 CMD='uv run --frozen pytest tests/test_rapports.py -k dod_1'
```

Le périmètre prouvé n'est pas paramétrable, et ce n'est pas une commodité perdue : `PATHS=tests`
rangeait une attestation qui n'engageait que `tests/`, si bien que tout `web/` pouvait être réécrit
sans périmer une seule preuve. Toute attestation porte désormais l'empreinte de `web`, `lib`,
`scripts`, `skills`, `alembic` et `tests` — de ceux, parmi eux, qui existent au HEAD.

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

**Seul `advance` y écrit** par construction, et seulement d'après des codes de sortie réels. La
liste d'interdits refuse à l'agent d'y écrire avec ses outils d'édition ; elle ne l'empêche pas d'y
écrire par un `sed -i` ou un script, faute de bac à sable. C'est une contrainte de conception, pas
une barrière.

## Échecs : tri par famille, pas compteur

Chaque check déclare la famille de son échec, et c'est elle qui commande la suite.

| Famille | Causes | Réponse |
|---|---|---|
| **A. Réparable** | test rouge, lint, attestation invalidée, rebase à faire, rouge manquant, definition of done mal formée | L'agent réessaie — travail normal |
| **B. Environnement** | environnement de développement injoignable, constaté par `doctor` | Arrêt immédiat, signalé comme panne |
| **C. Question métier** | critère ambigu, infaisable, périmètre flou | Retour au citizen developer |
| **D. Interdit** | contenu proscrit sous `paved-road/` sur un dépôt public | Arrêt : la décision remonte à un humain |

La famille est déclarée **par check**, pas par cause : `CHECKS` en fixe une par entrée. Aucun check
n'émet C aujourd'hui — la famille existe pour l'arrêt manuel de l'agent, pas pour un code de
sortie. Et un échec de `make security` dû au réseau sera restitué en A, à tort.

Réessayer sur A est légitime et fréquent ; réessayer sur B, C ou D est une erreur dès la première
fois.

### Plafond de la famille A — en observation

`advance` journalise le nombre d'échecs de famille A enchaînés depuis le dernier succès, **sans
agir**. La valeur du plafond sera choisie sur les données du milestone 1, pas devinée. Quand il
sera actif, il produira une **conversion en HITL checkpoint**, pas un échec : l'agent se met en
pause, il ne se débloque jamais lui-même.

## Le rouge avant le vert

`prove` refuse une attestation verte dont le rouge n'a pas été journalisé, et refuse aussi un vert
joué sur la même empreinte de périmètre que son rouge — rien n'ayant changé entre les deux, le
cycle n'a pas eu lieu. `advance --red` enregistre ce rouge : il exige un code de sortie non nul et
une commande aussi recevable que celle d'un vert, mais **pas** un arbre propre — c'est bien le
moment où le test existe et où le code n'existe pas encore. L'empreinte journalisée est celle du
HEAD, donc du code d'avant. Le vert, lui, exige un arbre propre : il inscrit une empreinte, et
elle ne décrirait pas un travail non committé.

Ce que cela démontre est modeste et il faut le dire : que le test cité a échoué sur un état du
code, et qu'il passe sur un autre. Cela ne dit pas que c'est *ce* changement qui l'a fait passer.
Un agent déterminé peut committer un octet entre les deux. Ce qui est fermé, c'est le cas courant
et le plus dommageable : écrire le test après le code, et ne l'avoir jamais vu échouer.

## L'antériorité de la DoD

`verify_dod` refuse un parcours dont un commit touchant `web/`, `lib/`, `skills/` ou `alembic/`
précède celui qui ajoute la definition of done. La fenêtre est celle de la branche, délimitée par
la merge-base avec `--base` (`origin/main` par défaut) ; quand cette base n'est pas résolvable, le
contrôle ne s'exerce pas, faute de savoir où commence le parcours.

Le contrôle lit l'ordre des commits : une réécriture d'historique l'efface. C'est un signal fort,
pas une garantie, et il ne faut pas le présenter autrement.

## L'immuabilité d'un contrat validé

Une fois la ligne « Validé par <qui> le <AAAA-MM-JJ> » committée, toute ligne de « Ce qui devra
marcher » qui change exige une ligne `Révision AAAA-MM-JJ` sous le critère concerné, et un critère
qui disparaît est refusé. C'est la règle qui empêche de rétrécir la cible jusqu'à ce que le vert
soit atteignable.

## Rien ne rejoue les preuves

La CI ne lit aucun artefact du parcours. Le verdict d'une attestation est celui de la commande qui
a tourné localement, sur l'empreinte de code qui y est inscrite.

C'est un choix, pas un oubli : la CI porte des tests, de la sécurité, des audits, des builds et des
déploiements ; elle ne relit pas des documents produits par le workflow de développement. Ce qui
tient la preuve, c'est que l'empreinte périme l'attestation dès que le code change, que la liste
d'interdits protège les attestations et le journal en écriture, et que le pair les lit dans la PR.

Ce qu'on perd, et qui est assumé : rien du côté GitHub ne constatera qu'une PR touchant `web/` a un
contrat démontré. La garantie est locale.
