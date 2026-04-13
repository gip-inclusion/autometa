# Spécification : Correction des alertes Dependabot

**Branche** : `002-fix-deps-security`
**Créée le** : 2026-04-13

Bumper deux dépendances transitives vulnérables dans `uv.lock` :

- `cryptography >= 46.0.7` — GHSA-p423-j2cm-9vmq / CVE-2026-39892 (medium, buffer overflow).
- `Pygments >= 2.20.0` — GHSA-5239-wwwm-4pmq / CVE-2026-4539 (low, ReDoS).

## Critères d'acceptation

- `uv.lock` référence les versions cibles.
- `make ci` passe.
- Les alertes Dependabot #4 et #5 passent à « fixed » après merge.
- Aucune modification de code applicatif.
