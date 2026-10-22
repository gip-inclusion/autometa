# DOD-2

**Critère** — [du brief : « j'ai un bouton de suggestion : republier »] Cette mention comporte un unique bouton « Republier » ; quand je clique dessus, toutes les versions en ligne en retard sont remises en ligne avec mon contenu actuel, chacune sur son environnement.
**Commande** — `uv run --frozen pytest tests/test_dashboards_routes.py::test_dod_2_suggestion_porte_un_bouton_republier_ciblant_les_versions_en_retard -q`
**Code de sortie** — 0
**Sortie** — 

```
.                                                                        [100%]
=============================== warnings summary ===============================
tests/test_dashboards_routes.py::test_dod_2_suggestion_porte_un_bouton_republier_ciblant_les_versions_en_retard
  /home/lelia/Documents/PDI/Matometa/tests/conftest.py:133: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
1 passed, 1 warning in 1.89s
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
