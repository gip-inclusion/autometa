# DOD-6

**Critère** — [du brief : « single cron.py for everything … same formulas / etc. with varying params »] Un seul cron produit un fichier de données par déclinaison déclarée, avec les mêmes calculs pour chacune, et rien d'autre : pas de fichier qui liste les déclinaisons. Une déclinaison non déclarée n'a pas de fichier, même si la source de données la connaît.
**Commande** — `uv run --frozen pytest tests/test_cron.py tests/test_dashboard_api.py tests/test_multi_source_template.py -k dod_6 -q`
**Code de sortie** — 0
**Sortie** — 

```
.......                                                                  [100%]
=============================== warnings summary ===============================
tests/test_cron.py::test_dod_6_publication_run_receives_the_dashboard_slug_not_the_composite
  /Users/louije/Development/gip/Autometa/tests/conftest.py:133: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
7 passed, 137 deselected, 1 warning in 1.11s
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `58b365eef7b9b035d9f68480c1d172f91e42fc07` |
| `lib` | `a7a421f061a11f05aaf02377b9c935640a68aa07` |
| `scripts` | `a4d9138781a04d96661f9e8647f4867cf513d756` |
| `skills` | `e1ac5c036de0d232af9c3e9fcdf21643e7ce045e` |
| `alembic` | `9dbb4fa33c1a7f59f3d1f956aa23798333baebf3` |
| `tests` | `7649e1e844a14ed0481e8aa963d4c2414bbe0854` |
| `browser` | `237931537134f569ff3228a21f44d3542707d581` |

**Verdict** — démontré.
