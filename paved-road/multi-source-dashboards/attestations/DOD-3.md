# DOD-3

**Critère** — [du brief : « /interactive/dashboard-name page with no ?q can be intercepted to show the toc »] Dans l'application, connecté, `/interactive/{slug}/` sans `?q` sur un tableau multi-sources affiche la liste des déclinaisons avec leur lien, et un lien vers la page d'édition. Un tableau de bord sans déclinaison n'est pas intercepté : il s'affiche comme aujourd'hui.
**Commande** — `uv run --frozen pytest tests/test_interactive_serving.py tests/test_dashboards_routes.py -k dod_3 -q`
**Code de sortie** — 0
**Sortie** — 

```
.......                                                                  [100%]
=============================== warnings summary ===============================
.venv/lib/python3.14/site-packages/fastapi/testclient.py:1
  /Users/louije/Development/gip/Autometa/.venv/lib/python3.14/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
7 passed, 96 deselected, 1 warning in 0.78s
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
