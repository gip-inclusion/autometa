# DOD-4

**Critère** — [du brief : « car sinon ce n'est pas publié »] Après la republication, la version en ligne active reflète mes changements et la suggestion disparaît ; si je recharge la page, l'état affiché correspond toujours à la réalité du serveur. En production, le lien public est stable et montre le nouveau contenu. En staging, republier crée un **nouveau** lien de test : l'ancien lien reste figé sur le contenu déjà partagé — c'est voulu, une version de test sert à faire vérifier un état précis, pas à être mutée sous les yeux de qui l'a reçue.
**Commande** — `uv run --frozen pytest tests/test_publication_drift.py -k dod_4 -q`
**Code de sortie** — 0
**Sortie** — 

```
.                                                                        [100%]
1 passed, 6 deselected in 0.69s
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `6949c9050c5a9d761c917f934bc190b050ebe6c6` |
| `lib` | `21e46bf4b524e6939ccf7a080591643bd9c5b683` |
| `scripts` | `292a403984c75249c2c2f0fdf5ab4fea8e0fbf98` |
| `skills` | `a17f23d627a1c18cf4a0ecd1f42d501d4667ea5d` |
| `alembic` | `4199ab20c8200527287a4d1328e495721ee59ab2` |
| `tests` | `9cb5eb29d7c02ef5d91866487eebcde62d98e85b` |
| `browser` | `0e22d10d4a1fbd411bc5db77ba166e82f28a7421` |

**Verdict** — démontré.
