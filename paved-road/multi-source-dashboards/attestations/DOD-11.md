# DOD-11

**Critère** — [état initial] Un tableau multi-sources sans aucune déclinaison déclarée l'indique sur la page d'édition (« Aucune déclinaison »), et son cron ne produit aucun fichier de données.
**Commande** — `uv run --frozen pytest tests/test_dashboards_routes.py tests/test_multi_source_template.py -k dod_11 -q`
**Code de sortie** — 0
**Sortie** — 

```
..                                                                       [100%]
=============================== warnings summary ===============================
tests/test_dashboards_routes.py::test_dod_11_detail_says_when_no_variant_is_declared
  /Users/louije/Development/gip/Autometa/.worktrees/multi-source-dashboards/tests/conftest.py:133: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
2 passed, 87 deselected, 1 warning in 1.13s
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `22e7f8897e3cc5fd322aef80ffaacbebf57705b1` |
| `lib` | `b02675ca62f3ed96f13b7f8baa2f0848af28b7db` |
| `scripts` | `a4d9138781a04d96661f9e8647f4867cf513d756` |
| `skills` | `492f69b14d8d3ac205c8acf424a21a52ccef1e8a` |
| `alembic` | `9dbb4fa33c1a7f59f3d1f956aa23798333baebf3` |
| `tests` | `0c1437442bfac189ccc90e7aabcdf3210534fda2` |
| `browser` | `e84a913b0c4e492f80b0c69655b3d975df4f39bb` |

**Verdict** — démontré.
