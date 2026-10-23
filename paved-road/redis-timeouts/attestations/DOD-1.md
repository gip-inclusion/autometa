# DOD-1

**Critère** — [du brief : « the redis timeout fix »] Quand la file d'attente accepte la connexion mais ne répond plus, Autometa s'en aperçoit en quelques secondes au lieu d'attendre indéfiniment, et continue d'essayer : un message envoyé après le retour du service reçoit sa réponse, sans redémarrage.
**Commande** — `uv run --frozen pytest tests/test_runner.py -k dod_1 -q`
**Code de sortie** — 0
**Sortie** — 

```
.                                                                        [100%]
1 passed, 65 deselected in 2.77s
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `81525a7f42be78e58fb89524481d47e5d0486d90` |
| `lib` | `b44e89c23fa8948a31759c6eeb906f1f13cf6473` |
| `scripts` | `1db5541ee291f83cc7f58352cd6e10d88881ebf6` |
| `skills` | `fbec123c7a780c89e7405a30f3cebc5b35bc519c` |
| `alembic` | `4199ab20c8200527287a4d1328e495721ee59ab2` |
| `tests` | `a4119d45d709c2832d11c0d04e1eb1575ad99133` |
| `browser` | `e1014cdcfb373eabc61d5901ed1e2eb8a1fc476e` |

**Verdict** — démontré.
