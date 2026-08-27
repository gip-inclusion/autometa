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

Aujourd'hui, seul le niveau L0 est en place, et il se tient **à la main** — aucune commande à lancer.

1. **Écrire la Definition of Done avant de coder.** Un fichier
   `paved-road/<nom-de-branche>/definition-of-done.md` qui dit, en français, ce qui devra marcher à
   la fin. Format et règles : `docs/paved-road/l0-definition-of-done.md`.
2. **La faire valider** par la personne qui a formulé la demande, en lui soumettant au plus cinq
   décisions, chacune avec un défaut déjà choisi. Ne rien dire, c'est accepter le défaut.
3. **Committer la DoD en premier.** Le premier commit de la branche est celui qui l'ajoute : c'est la
   seule chose qui distingue un accord convenu d'avance d'une DoD écrite après coup pour coller au
   code produit.
4. **Coder**, puis rédiger une attestation par critère sous
   `paved-road/<nom-de-branche>/attestations/` : la commande lancée, son code de sortie, le verdict.
5. **Ouvrir la PR** avec la DoD et les attestations dedans.

Une DoD validée ne se réécrit pas. Un critère qui se révèle infaisable est un blocage métier : il
remonte à la personne qui a formulé la demande, avec au moins deux options formulées en résultats
observables.

## Les règles que la DoD ne porte pas

Les invariants permanents — SQL paramétré, timeouts, migrations, sécurité — ne se recopient pas dans
chaque Definition of Done. Ils vivent dans `.claude/rules/`, dans `gates.toml` et dans la CI, et
protègent aussi le travail qui ne passe pas par le paved road.
