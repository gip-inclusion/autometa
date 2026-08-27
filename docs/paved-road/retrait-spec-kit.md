# Retrait de spec-kit — où sont passés les invariants

Deux parcours de spécification concurrents produiraient deux sources de vérité. spec-kit est retiré
au profit du paved road : les neuf commandes `/speckit.*`, `.specify/` et `specs/`.

La constitution (`.specify/memory/constitution.md`) portait en revanche des invariants qui gardent
leur valeur. Ils ont été récupérés avant suppression et redistribués selon la règle de partage de L0
— *invariant permanent → guardrail, contrainte propre à la demande → acceptance criterion*. **Aucun
n'a survécu comme document déclaratif** : un principe qu'on se contente de proclamer n'est vérifié
par personne.

| Principe de la constitution | Où il vit maintenant |
|---|---|
| I. Lean & Simple First, YAGNI, réutiliser avant d'écrire | `.claude/rules/code.md` — déjà couvert mot pour mot |
| II. OWASP : injection SQL | `.claude/rules/sql.md`, ruff `S608` en observation |
| II. OWASP : authentification, moindre privilège | `scripts/check_route_auth.py` + baseline `gates.toml`, `.claude/rules/securite.md` |
| II. Risques IA : sorties de modèle non fiables | `.claude/rules/securite.md` |
| II. TLS, secrets hors du code | `.claude/rules/securite.md`, ruff `S113`, `web/config.py` |
| II. Dépendances épinglées et auditées | `uv.lock`, job nightly `Dependencies`, `make deps-audit` |
| II. RGPD, minimisation des données | `.claude/rules/securite.md`, `.claude/rules/review.md`, `lib/pii.py` |
| III. Transparence, décisions documentées | `docs/plans/` — pratique déjà en place |
| IV. Impact mesurable | Instrumentation du milestone 1 (`lib/paved_road.py`) pour le parcours ; pour une demande, un chiffre devient un `DOD-N` et cite sa source (règle R2) |
| V. Lisibilité inter-équipes, français, glossaire | Format de la DoD (`docs/paved-road/l0-definition-of-done.md`), règle R3 |
| Section obligatoire « Modèle de menaces » | Dissoute : les menaces récurrentes sont des guardrails, `.claude/rules/zones-critiques.md` impose une relecture humaine sur les surfaces sensibles |
| Section obligatoire « Mesure d'impact » | Dissoute : une section remplie à chaque spec par obligation formelle n'a jamais été relue |
| Workflow : revue obligatoire, lint et tests avant merge | `required_status_checks`, `CODEOWNERS` (milestone 0) |
| Workflow : une PR = un changement logique | `.claude/rules/review.md` |
| Gouvernance : amendements, versionnement, conformité | Dissoute avec la constitution |

`specs/002-fix-deps-security/spec.md` était la seule spec produite. Son objet — bumper `cryptography`
et `Pygments` — est traité depuis par le job nightly `Dependencies`.
