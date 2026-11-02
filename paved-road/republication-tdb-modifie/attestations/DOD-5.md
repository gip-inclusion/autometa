# DOD-5

**Critère** — [tiré du brief : « un tableau de bord qui est publié »] Sur un tableau de bord qui n'a aucune version en ligne, aucune mention ni bouton de republication n'apparaît : il n'y a rien à republier.
**Commande** — `uv run --frozen pytest tests/test_publication_drift.py -k dod_5 -q`
**Code de sortie** — 0
**Sortie** — 

```
.                                                                        [100%]
1 passed, 4 deselected in 9.66s
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `36e23af902367ce3613c59efa923d0df27cb1e62` |
| `lib` | `e68ea84aa9eff2faa41a600fd3c8c13c24524953` |
| `scripts` | `1db5541ee291f83cc7f58352cd6e10d88881ebf6` |
| `skills` | `4417cbf8fc3ad72b05fc6e41363700cced396fec` |
| `alembic` | `4199ab20c8200527287a4d1328e495721ee59ab2` |
| `tests` | `cfecbbc1e527dec41ea2038f817e40281811b2ab` |
| `browser` | `436c5444cacbdc0a42d21ffb550953fda4b1ddae` |

**Verdict** — démontré.
