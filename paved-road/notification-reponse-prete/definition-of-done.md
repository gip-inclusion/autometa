# Notifier quand Autometa a fini de répondre

## Ce que je veux

Suite aux retours utilisateurs : quand Autometa finit de réfléchir et donne sa réponse,
la personne qui est partie sur un autre onglet doit être rappelée, comme sur Slack — une
pastille rouge sur l'onglet du navigateur et un son.

## Ce qui devra marcher

DOD-1 — [du brief : « une petite boule rouge dans l'onglet de l'utilisateur »] Quand Autometa
finit de répondre alors que je regarde un autre onglet ou une autre application, une pastille
rouge apparaît sur l'icône de l'onglet Autometa.

DOD-2 — [du brief : « un son associé »] Au même moment, un son court est joué pour signaler que
la réponse est prête.

DOD-3 — [du brief : « comme sur Slack »] Quand je reviens sur l'onglet Autometa, la pastille
rouge disparaît.

DOD-4 — [décision « onglet actif »] Si je regarde déjà l'onglet Autometa au moment où la réponse
arrive, rien ne se déclenche : ni son, ni pastille.

DOD-5 — [décision « fin sur erreur »] Si Autometa s'arrête sur une erreur au lieu d'une réponse,
la notification se déclenche quand même — même pastille, même son —, car la réflexion que
j'attendais est terminée.

DOD-6 — [décision « plusieurs réponses »] Si plusieurs conversations se terminent pendant mon
absence, l'onglet montre un simple point rouge, sans chiffre.

## Sources lues

- `web/static/js/stream.js` (R1) — écouteur de fin de réponse SSE (événement « done »),
  affichage et masquage de « Autometa réfléchit… ».
- `web/templates/base.html` (R1) — titre et favicon de l'onglet, ordre de chargement des scripts.
- `web/static/css/style.css` (R1) — styles de l'indicateur de chargement.
- `browser/test_socle.py`, `browser/conftest.py` (R1) — comment un résultat observable se prouve
  au navigateur (Playwright, marqueur `browser`).
- `CLAUDE.md`, `.claude/rules/code.md` (R5) — conventions front : vanilla JS + htmx, pas de
  bundler, biome pour le lint.
- Retours utilisateurs rapportés par le demandeur (R6) — origine du besoin.

## Questions ouvertes

Aucune.

## Validation

Validé par Annaelle Garcia le 2026-09-09.
