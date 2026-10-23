# DOD-4

**Critère** — [du brief : « enforce product health »] Si Autometa démarre pendant une coupure de la file, il reprend seul dès le retour du service : un message envoyé ensuite reçoit sa réponse, sans second redémarrage.
**Commande** — `uv run --frozen pytest tests/test_runner.py -k dod_4 -q`
**Code de sortie** — 0
**Sortie** — 

```
....                                                                     [100%]
4 passed, 62 deselected in 4.69s
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
