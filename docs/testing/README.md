# Stratégie de test

Cet espace décrit **pourquoi** et **comment** on teste ce dépôt. L'objectif tient en deux mots : **non-régression** (rien de cassé n'entre) et **anti-slop** (aucun test vert-mais-creux ne compte), dans un repo développé massivement par des agents IA.

Le fil conducteur de tout le dispositif :

> Une règle est un **espoir** (« l'agent devrait tester »). Une vérification déterministe est une **loi** (« la CI échoue sinon »). Chaque pièce de la stratégie convertit un espoir en loi — et pose un **cliquet** : un plancher qui, une fois posé, ne peut plus que monter.

## Les documents

| Doc | Pour qui | Contenu |
|---|---|---|
| [`01-pourquoi.md`](01-pourquoi.md) | **tout le monde, non-techs inclus** | La philosophie en langage humain : la dette qu'on assume, qu'on gèle, puis qu'on rembourse. À lire en premier. |
| [`02-strategie.md`](02-strategie.md) | techs | La stratégie : le modèle en cercles concentriques, les niveaux de test, le catalogue des mécanismes, la fondation « contrats », le double circuit LLM, la justesse des données, l'art d'écrire un test. |
| [`03-roadmap.md`](03-roadmap.md) | techs / pilotage | L'orchestration : l'ordre réel par dépendances, ce qui est parallélisable, les couplages à ne pas rater, la gouvernance du cliquet. |
| [`04-phases.md`](04-phases.md) | techs | Le pourquoi/comment **et la mise en place concrète** de chaque phase : problème résolu, garantie ajoutée, cliquet, et les artefacts exacts à produire. |
| [`05-mise-en-oeuvre.md`](05-mise-en-oeuvre.md) | techs / pilotage | **Le runbook autoportant pour démarrer et reprendre** : stratégie projet, carte d'intégration au dépôt, définition de « fait » par phase, prochaine action déroulée, protocole de reprise. |

## Par où commencer

- **Tu découvres le sujet** → [`01-pourquoi.md`](01-pourquoi.md), puis [`02-strategie.md`](02-strategie.md).
- **Tu veux implémenter (ou reprendre)** → [`05-mise-en-oeuvre.md`](05-mise-en-oeuvre.md) en premier (c'est le point d'entrée exécutable), avec [`03-roadmap.md`](03-roadmap.md) pour l'ordre et [`04-phases.md`](04-phases.md) pour le détail de chaque étape.
- **Tu écris un test maintenant** → la section « L'art d'écrire un test » de [`02-strategie.md`](02-strategie.md), et `.claude/rules/tests.md`.

## Ancrage

Stratégie tirée du motif réel des gros projets Python qui scalent (FastAPI, Sentry, Home Assistant, Airflow, Polar, Pydantic, Litestar, Great Expectations) et des références méthodologiques (Practical Test Pyramid de Fowler, Software Engineering at Google ch. 11–14, guides Anthropic sur les évals et le dev assisté par IA). Enseignement central : **la garantie qu'un test existe et qu'il vérifie vraiment vient des gates déterministes, pas d'une règle de nommage ni de la bonne volonté de l'agent.**
