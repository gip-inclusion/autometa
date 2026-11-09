# DOD-4

**Critère** — [du brief : « enforce product health »] Si Autometa démarre pendant une coupure de la file, il reprend seul dès le retour du service : un message envoyé ensuite reçoit sa réponse, sans second redémarrage.
**Commande** — `uv run --frozen pytest tests/test_runner.py -k dod_4 -q`
**Code de sortie** — 0
**Sortie** — 

```
....                                                                     [100%]
4 passed, 62 deselected in 4.60s
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
