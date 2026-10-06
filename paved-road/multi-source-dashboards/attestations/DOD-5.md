# DOD-5

**Critère** — [du brief : « links to every db, and json with mapping is accessible on the dashboard/xxxxxx/edit page »] La page d'édition liste chaque déclinaison avec son libellé, son lien interne, son lien public quand une publication est active, et propose un lien vers le JSON du mapping (clé, libellé, jeton, liens).
**Commande** — `uv run --frozen pytest tests/test_interactive_serving.py tests/test_dashboards_routes.py -k dod_5 -q`
**Code de sortie** — 0
**Sortie** — 

```
..                                                                       [100%]
=============================== warnings summary ===============================
.venv/lib/python3.14/site-packages/fastapi/testclient.py:1
  /Users/louije/Development/gip/Autometa/.venv/lib/python3.14/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
2 passed, 101 deselected, 1 warning in 1.18s
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `198be3e0ca19c7344346b460f47632a7997c1a8b` |
| `lib` | `84a1e7d287295a59e01cb7c7538590bc2859cd10` |
| `scripts` | `1db5541ee291f83cc7f58352cd6e10d88881ebf6` |
| `skills` | `7b027d42d1f92f23e8e4d4564a145642ca751e07` |
| `alembic` | `4199ab20c8200527287a4d1328e495721ee59ab2` |
| `tests` | `ec3304b8db8c97656f9df8252c87a26ab455a11c` |
| `browser` | `3838fcc50ff5c25b4f975d5d2bdbc060a2ca9cca` |

**Verdict** — démontré.
