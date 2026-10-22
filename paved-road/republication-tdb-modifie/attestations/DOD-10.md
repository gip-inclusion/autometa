# DOD-10

**Critère** — [Révision 2026-10-20, du brief : « quand je suis dans une conversation en train de faire des modif sur un tableau de bord publié, il faut que j'aie une alerte sur le fait que je dois republier »] Quand, dans une conversation, l'assistant vient de modifier un tableau de bord que j'ai déjà publié, une alerte apparaît dans la conversation : elle m'indique que mes changements ne seront visibles en ligne qu'après republication et m'offre un accès direct pour aller republier le tableau concerné.
**Commande** — `uv run --frozen pytest tests/test_conversation_dashboards.py::test_dod_10_conversation_signale_un_tableau_publie_modifie_depuis -q`
**Code de sortie** — 0
**Sortie** — 

```
.                                                                        [100%]
=============================== warnings summary ===============================
tests/test_conversation_dashboards.py::test_dod_10_conversation_signale_un_tableau_publie_modifie_depuis
  /home/lelia/Documents/PDI/Matometa/tests/conftest.py:133: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
1 passed, 1 warning in 1.66s
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
