# DOD-7

**Critère** — [garde-fou : tableau non publiable] Sur un tableau de bord devenu non publiable (il utilise l'API query) alors qu'il garde une version en ligne, aucun bouton de republication n'apparaît, et un message m'explique que republier est indisponible.
**Commande** — `uv run --frozen pytest tests/test_dashboards_routes.py::test_dod_7_bouton_republier_reserve_aux_tableaux_publiables -q`
**Code de sortie** — 0
**Sortie** — 

```
.                                                                        [100%]
=============================== warnings summary ===============================
tests/test_dashboards_routes.py::test_dod_7_bouton_republier_reserve_aux_tableaux_publiables
  /home/lelia/Documents/PDI/Matometa/tests/conftest.py:134: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
1 passed, 1 warning in 1.68s
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `6949c9050c5a9d761c917f934bc190b050ebe6c6` |
| `lib` | `21e46bf4b524e6939ccf7a080591643bd9c5b683` |
| `scripts` | `292a403984c75249c2c2f0fdf5ab4fea8e0fbf98` |
| `skills` | `a17f23d627a1c18cf4a0ecd1f42d501d4667ea5d` |
| `alembic` | `4199ab20c8200527287a4d1328e495721ee59ab2` |
| `tests` | `9cb5eb29d7c02ef5d91866487eebcde62d98e85b` |
| `browser` | `0e22d10d4a1fbd411bc5db77ba166e82f28a7421` |

**Verdict** — démontré.
