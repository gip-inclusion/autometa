# DOD-20

**Critère** — [précision du demandeur : la liste ou le mapping ne doit pas être dans le code du TDB] Publier ou rafraîchir la publication d'un tableau multi-sources est refusé, avec la raison affichée sur la page d'édition, si un jeton déclaré apparaît dans le contenu d'un fichier du tableau (page, script, fichier de données ou autre). Le seul emplacement admis d'un jeton est le nom du fichier `data/{jeton}.json`. Une liste de clés ou de libellés dans le code n'est pas refusée : seul le jeton ouvre l'accès.
**Commande** — `uv run --frozen pytest tests/test_variants_lib.py tests/test_publications.py tests/test_cron.py tests/test_dashboards_routes.py -k dod_20 -q`
**Code de sortie** — 0
**Sortie** — 

```
.......                                                                  [100%]
=============================== warnings summary ===============================
tests/test_publications.py::test_dod_20_publish_is_refused_when_a_file_carries_a_token
  /Users/louije/Development/gip/Autometa/tests/conftest.py:133: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
7 passed, 225 deselected, 1 warning in 1.37s
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
