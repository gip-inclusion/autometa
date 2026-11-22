# Lire le CRM Attio

## Ce que je veux

Les bizdevs vont suivre leurs prospects dans Attio, le CRM de l'équipe. Je veux qu'Autometa puisse lire ce CRM : qu'un agent compte une cible ou retrouve une structure, et qu'un tableau de bord suive un pipe. Autometa n'écrit jamais dans Attio.

## Ce qui devra marcher

DOD-1 — Quand je demande à l'agent combien de structures d'un type compte le CRM, il répond avec le total et la répartition lus dans Attio.

DOD-2 — Quand je demande à l'agent de retrouver des structures ou des contacts selon un critère (type, département, source), il rend la liste lue dans Attio, 500 enregistrements au plus.

DOD-3 — Un tableau de bord lit les entrées d'un pipe Attio, depuis son cron ou en direct depuis sa page.

DOD-4 — Ce qu'un tableau de bord lit dans Attio ne contient aucun email ni aucun téléphone.

DOD-5 — Une demande d'écriture, ou une lecture que le connecteur ne prévoit pas, est refusée avant tout appel à Attio, avec un message qui dit ce qui est permis.

DOD-6 — La page « Sources de données » montre Attio et dit s'il répond.

## Sources lues

- `CONTRIBUTING.md` et `docs/paved-road/l0-definition-of-done.md` : format de ce fichier.
- `docs/interactive-dashboards.md` : la façade et `/api/query`, par où un tableau lit une source.
- `.claude/rules/review.md` : une PR par changement logique, aucune donnée personnelle dans le dépôt public.

## Questions ouvertes

1. Dans un tableau, les noms des contacts sortent, et leurs emails et téléphones sont retirés. Défaut retenu : on garde ce choix.
2. Un comptage de toutes les structures prend une trentaine de secondes. Défaut retenu : il se fait dans le cron du tableau, et la documentation le dit, sans cache ajouté par le connecteur.

## Validation

Validé par Mehdi Aïda le 2026-11-22.
