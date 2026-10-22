# DOD-1

**Critère** — [du brief : « Si je change un tableau de bord qui est publié »] Quand j'ouvre la page d'un tableau de bord dont au moins une version en ligne est en retard sur mes changements, une mention visible m'avertit que la version en ligne ne reflète pas mes derniers changements — y compris lorsqu'une autre version en ligne, elle, est déjà à jour.
**Commande** — `uv run --frozen pytest tests/test_publication_drift.py -k dod_1 -q`
**Code de sortie** — 0
**Sortie** — 

```
.                                                                        [100%]
1 passed, 4 deselected in 7.01s
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
