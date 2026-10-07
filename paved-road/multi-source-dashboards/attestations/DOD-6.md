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
7 passed, 156 deselected, 1 warning in 1.12s
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `198be3e0ca19c7344346b460f47632a7997c1a8b` |
| `lib` | `857b7b5f0d013efe0b7a0a185fffe090db79d3a7` |
| `scripts` | `1db5541ee291f83cc7f58352cd6e10d88881ebf6` |
| `skills` | `c249e7699a8914d4f455daef4f8a468d8af21af6` |
| `alembic` | `4199ab20c8200527287a4d1328e495721ee59ab2` |
| `tests` | `0aa8b2c2bad0ad3775012775d4eba5752186eb87` |
| `browser` | `3838fcc50ff5c25b4f975d5d2bdbc060a2ca9cca` |

**Verdict** — démontré.
