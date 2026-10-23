# DOD-3

**Critère** — [du brief : « the redis timeout fix »] Quand la file d'attente ne répond plus, le titre et les étiquettes d'une nouvelle conversation sont tout de même générés, après quelques secondes d'attente au plus.
**Commande** — `uv run --frozen pytest tests/test_engine_limits.py -k dod_3 -q`
**Code de sortie** — 0
**Sortie** — 

```
.                                                                        [100%]
1 passed, 3 deselected in 0.47s
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `81525a7f42be78e58fb89524481d47e5d0486d90` |
| `lib` | `b44e89c23fa8948a31759c6eeb906f1f13cf6473` |
| `scripts` | `1db5541ee291f83cc7f58352cd6e10d88881ebf6` |
| `skills` | `fbec123c7a780c89e7405a30f3cebc5b35bc519c` |
| `alembic` | `4199ab20c8200527287a4d1328e495721ee59ab2` |
| `tests` | `adadd9d444e0674cd68d799e7d19dc91efd93937` |
| `browser` | `e1014cdcfb373eabc61d5901ed1e2eb8a1fc476e` |

**Verdict** — démontré.
