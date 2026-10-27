# DOD-3

**Critère** — [du brief : « the redis timeout fix »] Quand la file d'attente ne répond plus, le titre et les étiquettes d'une nouvelle conversation sont tout de même générés, après quelques secondes d'attente au plus.
**Commande** — `uv run --frozen pytest tests/test_engine_limits.py -k dod_3 -q`
**Code de sortie** — 0
**Sortie** — 

```
.                                                                        [100%]
1 passed, 3 deselected in 0.46s
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `5744b5c5ae2060b406e1849e0072a7c55c5d773c` |
| `lib` | `b44e89c23fa8948a31759c6eeb906f1f13cf6473` |
| `scripts` | `1db5541ee291f83cc7f58352cd6e10d88881ebf6` |
| `skills` | `fbec123c7a780c89e7405a30f3cebc5b35bc519c` |
| `alembic` | `4199ab20c8200527287a4d1328e495721ee59ab2` |
| `tests` | `07648e702a0abf2e04eae7e075d99365f9403229` |
| `browser` | `e1014cdcfb373eabc61d5901ed1e2eb8a1fc476e` |

**Verdict** — démontré.
