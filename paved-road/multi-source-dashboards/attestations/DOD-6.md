# DOD-6

**Critère** — [du brief : « single cron.py for everything … same formulas / etc. with varying params »] Un seul cron produit un fichier de données par déclinaison déclarée, avec les mêmes calculs pour chacune, et rien d'autre : pas de fichier qui liste les déclinaisons. Une déclinaison non déclarée n'a pas de fichier, même si la source de données la connaît.
**Commande** — `uv run --frozen pytest tests/test_cron.py tests/test_dashboard_api.py tests/test_multi_source_template.py -k dod_6 -q`
**Code de sortie** — 0
**Sortie** — 

```
.......                                                                  [100%]
=============================== warnings summary ===============================
tests/test_cron.py::test_dod_6_publication_run_receives_the_dashboard_slug_not_the_composite
  /Users/louije/Development/gip/autometa-multi-source/tests/conftest.py:133: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
7 passed, 156 deselected, 1 warning in 1.21s
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `025f36cf58659e483324d1a6cfc73a6df9549b0a` |
| `lib` | `24dea1b178864a4e9d2d459702281b8dd5467486` |
| `scripts` | `1db5541ee291f83cc7f58352cd6e10d88881ebf6` |
| `skills` | `4cd9e2f4ac9726e2a7cfd34ece88e82aaea1f745` |
| `alembic` | `4199ab20c8200527287a4d1328e495721ee59ab2` |
| `tests` | `5b7ce2570650d81cd71ce8c342b44d048849b78f` |
| `browser` | `3838fcc50ff5c25b4f975d5d2bdbc060a2ca9cca` |

**Verdict** — démontré.
