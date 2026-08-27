# Contribuer

## Démarrer de zéro

```bash
# 1. Cloner le repo et s'y placer
git clone https://github.com/votre-org/autometa.git
cd autometa

# 2. Installer l'environnement de développement
make setup

# 3. Vérifier que tout est en place — chaque échec est une phrase actionnable
make doctor

# 4. Lancer Claude Code
claude
```

## Développer une fonctionnalité

Le projet suit le **paved road** : un parcours unique, qui ajoute une contrainte à la fois. Sa
conception et sa justification sont dans `docs/plans/2026-07-28-autometa-paved-road-design.md`.

Les niveaux L0 et L1 sont en place. L0 se tient à la main ; L1 s'outille par quatre cibles du
`Makefile`, qui refusent de faire progresser le parcours sans code de sortie 0.

1. **Écrire la Definition of Done avant de coder.** Un fichier
   `paved-road/<nom-de-branche>/definition-of-done.md` qui dit, en français, ce qui devra marcher à
   la fin. Format et règles : `docs/paved-road/l0-definition-of-done.md`.
2. **La faire valider** par la personne qui a formulé la demande, en lui soumettant au plus cinq
   décisions, chacune avec un défaut déjà choisi. Ne rien dire, c'est accepter le défaut.
3. **Committer la DoD en premier.** Le premier commit de la branche est celui qui l'ajoute : c'est la
   seule chose qui distingue un accord convenu d'avance d'une DoD écrite après coup pour coller au
   code produit.
4. **Coder**, puis démontrer chaque critère par une commande réelle :
   `make paved-road-advance DOD=DOD-1 CMD='…'` range l'attestation correspondante — la commande, son
   code de sortie, les empreintes du contenu prouvé, le verdict. Format et règles :
   `docs/paved-road/l1-attestation.md`.
5. **Ouvrir la PR** avec la DoD, le journal et les attestations dedans.

`make paved-road-status` dit à tout moment l'état atteint et quels critères restent à démontrer.
Aucune image et aucun binaire sous `attestations/` : le dépôt est public, et un check le refuse.

Une DoD validée ne se réécrit pas. Un critère qui se révèle infaisable est un blocage métier : il
remonte à la personne qui a formulé la demande, avec au moins deux options formulées en résultats
observables.

## Les règles que la DoD ne porte pas

Les invariants permanents — SQL paramétré, timeouts, migrations, sécurité — ne se recopient pas dans
chaque Definition of Done. Ils vivent dans `.claude/rules/`, dans `gates.toml` et dans la CI, et
protègent aussi le travail qui ne passe pas par le paved road.
