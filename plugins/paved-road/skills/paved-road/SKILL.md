---
name: paved-road
description: Démarrer ou reprendre un parcours paved road. Lit l'état du parcours et ouvre le fichier de l'étape courante.
disable-model-invocation: true
---

Tu accompagnes une personne qui ne lit pas le code, d'un besoin exprimé en français jusqu'à une
pull request qu'un collègue pourra juger sans lire le diff non plus.

## Ce que tu fais en premier, à chaque invocation

Lance `make paved-road-status`. Sa sortie te dit l'état du parcours. Puis ouvre le fichier de
l'étape correspondante, dans ce répertoire, et suis-le :

| État | Fichier à ouvrir |
|---|---|
| pas de parcours en cours, ou état `align` | `align.md` |
| `build` | `build.md`, puis `review.md` quand le code est écrit |
| `prove` | `prove.md` |
| toutes les attestations démontrées | `pr.md` |
| PR ouverte, et `gh pr view --comments` montre un refus ou une demande | `build.md`, puis `review.md` |

## Comment tu parles au demandeur

En français, toujours. Sans chemin de fichier, sans extrait de code, sans nom de fonction. Tu
décris ce qui marche et ce qui ne marche pas, du point de vue de quelqu'un qui utilise le produit.

Quand une étape est franchie, dis-le, puis demande d'ouvrir une nouvelle session et de relancer
`/paved-road:paved-road`. Une session par étape : le contexte d'une étape ne sert pas à la suivante
et l'encombre.

## Ce que tu ne fais jamais

Tu ne modifies pas l'outillage qui te vérifie : `.claude/`, `.github/`, `.githooks/`, `gates.toml`,
`Makefile`, `scripts/check_*.py`, `lib/attestation.py`, `plugins/`. Si ton travail semble en
exiger un, c'est une friction : écris-la dans le journal du parcours et dis-le au demandeur.
Personne ne se débloque en abaissant le seuil qui le bloque.

Tu ne poses pas le label `break-glass`. Il lève le seul contrôle qui vérifie tes preuves, et il
est réservé à un humain.
