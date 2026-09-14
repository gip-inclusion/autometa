# DOD-18

**Critère** — [lentille gap-hunter : volume] Au-delà de 20 déclinaisons, la page d'édition affiche le compte (« 107 déclinaisons ») et un champ de filtre sur la clé et le libellé, en gardant la liste complète dans la page pour permettre un copier-coller de tous les liens.
**Commande** — `uv run --frozen pytest tests/test_interactive_serving.py tests/test_dashboards_routes.py -k dod_18 -q`
**Code de sortie** — 0
**Sortie** — 

```
..                                                                       [100%]
=============================== warnings summary ===============================
.venv/lib/python3.14/site-packages/fastapi/testclient.py:1
  /Users/louije/Development/gip/Autometa/.worktrees/multi-source-dashboards/.venv/lib/python3.14/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
2 passed, 91 deselected, 1 warning in 1.06s
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `fc7ea2412f4440b60688cde4af450c28a87036cf` |
| `lib` | `dc9847fa9b2068ea45fa108a5b65181732339298` |
| `scripts` | `a4d9138781a04d96661f9e8647f4867cf513d756` |
| `skills` | `7909438b122995b1a074b7e22d91284e5dc06587` |
| `alembic` | `9dbb4fa33c1a7f59f3d1f956aa23798333baebf3` |
| `tests` | `673cde27ace5f05aba230ca875362a9c3a4ea86e` |
| `browser` | `e84a913b0c4e492f80b0c69655b3d975df4f39bb` |

**Verdict** — démontré.
