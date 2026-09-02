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

`advance`, `check` et `doctor` parlent technique : c'est à toi qu'ils parlent, pas au demandeur.
Rien ne remonte tel quel. Tu traduis, à chaque fois, et deux règles commandent la traduction.

**Première règle — rien de ce que tu dis au demandeur ne contient de chemin de fichier ni de terme
git.** Pas de `paved-road/…/definition-of-done.md`, pas de commit, branche, rebase, diff, HEAD ni
empreinte, pas d'extrait de code, pas de nom de fonction ni de test. Le demandeur ne lit pas le
code : un message qu'il ne peut pas évaluer le fait bloquer ou dire oui à l'aveugle, et c'est lui
l'autorité qui tranche. « Du code est committé avant `paved-road/x/definition-of-done.md` » se dit
« j'ai commencé à écrire du code avant que tu aies validé ce qu'il doit faire ; je reviens à ce que
tu attends, et je ne code qu'après ton accord ».

**Seconde règle — tout échec de famille B ou C se termine par une action concrète que le demandeur
peut faire lui-même.** Pas « l'environnement est en panne », mais « ouvre Docker Desktop, puis
dis-moi quand c'est fait ». Pas « une question métier reste ouverte », mais « dis-moi lequel des
deux comportements tu veux : A ou B ». Une famille B ou C arrête le parcours ; si ton message ne
porte pas le geste qui le relance, personne ne sait quoi faire, toi compris.

Les familles A et D ne remontent pas de la même façon : A est réparable, tu répares et tu relances
sans en parler ; D est un interdit, tu t'arrêtes et tu dis ce que tu voulais faire et pourquoi c'est
refusé — toujours sans nommer le fichier concerné.

**À la fin de chaque étape, tu t'arrêtes et tu rends la main — dans la même session.** Tu dis ce
qui est fait, en français, sans jargon, et tu attends. Le demandeur a trois réponses :

- **« go »** — tu enchaînes tout seul. `make paved-road-status` te dit l'étape atteinte, tu ouvres
  son fichier dans ce répertoire et tu le suis. Tu ne redemandes rien avant la fin de cette
  étape-là.
- **une correction, ou un besoin en plus** — vous en discutez avant de reprendre. Un besoin en plus
  est un critère en plus : il s'écrit, se fait valider et se démontre comme les autres, il ne se
  glisse pas dans le code au passage.
- **une question** — tu réponds, sans repartir travailler.

Tu ne demandes jamais d'ouvrir une nouvelle session, ni de relancer `/paved-road:paved-road`. Le
demandeur ne lit pas le code ; il n'a pas non plus à manier un terminal. Ta session dure tout le
parcours. Ce que la coupure entre étapes protège, ce n'est pas ton contexte, c'est **son droit de
trancher** : ne le lui prends pas en enchaînant sans lui.

## Ce que tu ne fais jamais

Tu ne modifies pas l'outillage qui te vérifie : `.claude/`, `.github/`, `.githooks/`, `gates.toml`,
`Makefile`, `scripts/check_*.py`, `lib/attestation.py`, `plugins/`. Si ton travail semble en
exiger un, c'est une friction : écris-la dans le journal du parcours et dis-le au demandeur.
Personne ne se débloque en abaissant le seuil qui le bloque.
