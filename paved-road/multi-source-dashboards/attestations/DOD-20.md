# DOD-20

**Critère** — [précision du demandeur : la liste ou le mapping ne doit pas être dans le code du TDB] Publier ou rafraîchir la publication d'un tableau multi-sources est refusé, avec la raison affichée sur la page d'édition, si un jeton déclaré apparaît dans le contenu d'un fichier du tableau (page, script, fichier de données ou autre). Le seul emplacement admis d'un jeton est le nom du fichier `data/{jeton}.json`. Une liste de clés ou de libellés dans le code n'est pas refusée : seul le jeton ouvre l'accès.
**Commande** — `uv run --frozen pytest tests/test_variants_lib.py tests/test_publications.py tests/test_cron.py tests/test_dashboards_routes.py -k dod_20 -q`
**Code de sortie** — 0
**Sortie** — 

```
.......                                                                  [100%]
=============================== warnings summary ===============================
tests/test_publications.py::test_dod_20_publish_is_refused_when_a_file_carries_a_token
  /Users/louije/Development/gip/Autometa/.worktrees/multi-source-dashboards/tests/conftest.py:133: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
7 passed, 215 deselected, 1 warning in 1.48s
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
