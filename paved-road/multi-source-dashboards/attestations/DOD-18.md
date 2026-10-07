# DOD-18

**Critère** — [lentille gap-hunter : volume] Au-delà de 20 déclinaisons, la page d'édition affiche le compte (« 107 déclinaisons ») et un champ de filtre sur la clé et le libellé, en gardant la liste complète dans la page pour permettre un copier-coller de tous les liens.
**Commande** — `uv run --frozen pytest tests/test_interactive_serving.py tests/test_dashboards_routes.py -k dod_18 -q`
**Code de sortie** — 0
**Sortie** — 

```
..                                                                       [100%]
=============================== warnings summary ===============================
.venv/lib/python3.14/site-packages/fastapi/testclient.py:1
  /Users/louije/Development/gip/autometa-multi-source/.venv/lib/python3.14/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
2 passed, 101 deselected, 1 warning in 1.11s
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `025f36cf58659e483324d1a6cfc73a6df9549b0a` |
| `lib` | `857b7b5f0d013efe0b7a0a185fffe090db79d3a7` |
| `scripts` | `1db5541ee291f83cc7f58352cd6e10d88881ebf6` |
| `skills` | `4cd9e2f4ac9726e2a7cfd34ece88e82aaea1f745` |
| `alembic` | `4199ab20c8200527287a4d1328e495721ee59ab2` |
| `tests` | `5e5459c774ff6e8e55e094e1d678b509109e3517` |
| `browser` | `3838fcc50ff5c25b4f975d5d2bdbc060a2ca9cca` |

**Verdict** — démontré.
