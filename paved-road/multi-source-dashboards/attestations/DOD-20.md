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
7 passed, 224 deselected, 1 warning in 1.24s
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
