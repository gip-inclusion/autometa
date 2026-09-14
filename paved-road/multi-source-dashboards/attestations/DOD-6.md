# DOD-6

**Critère** — [du brief : « single cron.py for everything … same formulas / etc. with varying params »] Un seul cron produit un fichier de données par déclinaison déclarée, avec les mêmes calculs pour chacune, et rien d'autre : pas de fichier qui liste les déclinaisons. Une déclinaison non déclarée n'a pas de fichier, même si la source de données la connaît.
**Commande** — `uv run --frozen pytest tests/test_cron.py tests/test_dashboard_api.py tests/test_multi_source_template.py -k dod_6 -q`
**Code de sortie** — 0
**Sortie** — 

```
.......                                                                  [100%]
=============================== warnings summary ===============================
tests/test_cron.py::test_dod_6_publication_run_receives_the_dashboard_slug_not_the_composite
  /Users/louije/Development/gip/Autometa/.worktrees/multi-source-dashboards/tests/conftest.py:133: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
7 passed, 134 deselected, 1 warning in 1.08s
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
