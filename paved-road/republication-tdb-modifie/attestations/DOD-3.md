# DOD-3

**Critère** — [décision : confirmation production] Si la version publique (« production ») fait partie des versions à republier, une confirmation m'est demandée avant de remplacer la version vue par tout le monde ; une version de test (« staging ») seule se republie sans confirmation.
**Commande** — `uv run --frozen pytest tests/test_dashboards_routes.py::test_dod_3_confirmation_production_signalee_sur_le_bouton -q`
**Code de sortie** — 0
**Sortie** — 

```
..                                                                       [100%]
=============================== warnings summary ===============================
tests/test_dashboards_routes.py::test_dod_3_confirmation_production_signalee_sur_le_bouton[production-true]
  /home/lelia/Documents/PDI/Matometa/tests/conftest.py:133: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
2 passed, 1 warning in 1.89s
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
