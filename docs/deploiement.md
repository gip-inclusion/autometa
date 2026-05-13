# Mise en prod

Staging se déploie tout seul à chaque push sur `main`. Pour la prod, deux options.

## Tag de release

```bash
git checkout main && git pull
git tag v1.2.3 && git push origin v1.2.3
```

Format obligatoire `vMAJOR.MINOR.PATCH` (pas de suffixe).

## Choisir le numéro

- **PATCH** : fix, refacto, sécurité.
- **MINOR** : feature, ajout rétro-compatible.
- **MAJOR** : breaking change.

```bash
git fetch --tags && git tag --sort=-v:refname | head -5
```
