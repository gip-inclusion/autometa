# DOD-19

**Critère** — [lentille gap-hunter : fuite du jeton ; précision du demandeur] Matomo suit chaque déclinaison sous une URL lisible, `/interactive/{slug}/{clé}/`, transmise au traceur à la place de l'URL réelle : la clé et le libellé sont écrits par le cron dans le fichier de données, le jeton n'y figure jamais. Le jeton ne sort pas de l'URL : ni dans l'URL suivie par Matomo, ni dans le titre de l'onglet, ni dans le nom des fichiers exportés.
**Commande** — `uv run --frozen pytest browser/test_variants_page.py tests/test_dashboards_routes.py -k dod_19 -q`
**Code de sortie** — 0
**Sortie** — 

```
....                                                                     [100%]
=============================== warnings summary ===============================
tests/test_dashboards_routes.py::test_dod_19_detail_warns_when_the_page_of_a_converted_dashboard_can_leak_the_token[multi-template]
  /Users/louije/Development/gip/Autometa/tests/conftest.py:133: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
4 passed, 89 deselected, 1 warning in 2.75s
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
