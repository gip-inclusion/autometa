# DOD-19

**Critère** — [lentille gap-hunter : fuite du jeton ; précision du demandeur] Matomo suit chaque déclinaison sous une URL lisible, `/interactive/{slug}/{clé}/`, transmise au traceur à la place de l'URL réelle : la clé et le libellé sont écrits par le cron dans le fichier de données, le jeton n'y figure jamais. Le jeton ne sort pas de l'URL : ni dans l'URL suivie par Matomo, ni dans le titre de l'onglet, ni dans le nom des fichiers exportés.
**Commande** — `uv run --frozen pytest browser/test_variants_page.py tests/test_dashboards_routes.py -k dod_19 -q`
**Code de sortie** — 0
**Sortie** — 

```
....                                                                     [100%]
=============================== warnings summary ===============================
tests/test_dashboards_routes.py::test_dod_19_detail_warns_when_the_page_of_a_converted_dashboard_can_leak_the_token[multi-template]
  /Users/louije/Development/gip/Autometa/.worktrees/multi-source-dashboards/tests/conftest.py:133: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
4 passed, 89 deselected, 1 warning in 2.12s
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `a9e9273de118212994ef9e90dda9465eeeb907c5` |
| `lib` | `b02675ca62f3ed96f13b7f8baa2f0848af28b7db` |
| `scripts` | `a4d9138781a04d96661f9e8647f4867cf513d756` |
| `skills` | `492f69b14d8d3ac205c8acf424a21a52ccef1e8a` |
| `alembic` | `9dbb4fa33c1a7f59f3d1f956aa23798333baebf3` |
| `tests` | `86afe6cce9a5bc608482aa89360d70a8abd9dfc9` |
| `browser` | `220f7cad51a41efbefd065e26af541c0f2cc5999` |

**Verdict** — démontré.
