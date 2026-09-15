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
7 passed, 137 deselected, 1 warning in 1.15s
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `14f1d267ea8f25600f6ffefbb9007e08ed3b567e` |
| `lib` | `b02675ca62f3ed96f13b7f8baa2f0848af28b7db` |
| `scripts` | `a4d9138781a04d96661f9e8647f4867cf513d756` |
| `skills` | `492f69b14d8d3ac205c8acf424a21a52ccef1e8a` |
| `alembic` | `9dbb4fa33c1a7f59f3d1f956aa23798333baebf3` |
| `tests` | `a2ca65a4637f982a263f66790c95d57aa57fdb62` |
| `browser` | `220f7cad51a41efbefd065e26af541c0f2cc5999` |

**Verdict** — démontré.
