# DOD-3

**Critère** — [du brief : « /interactive/dashboard-name page with no ?q can be intercepted to show the toc »] Dans l'application, connecté, `/interactive/{slug}/` sans `?q` sur un tableau multi-sources affiche la liste des déclinaisons avec leur lien, et un lien vers la page d'édition. Un tableau de bord sans déclinaison n'est pas intercepté : il s'affiche comme aujourd'hui.
**Commande** — `uv run --frozen pytest tests/test_interactive_serving.py tests/test_dashboards_routes.py -k dod_3 -q`
**Code de sortie** — 0
**Sortie** — 

```
.....                                                                    [100%]
=============================== warnings summary ===============================
.venv/lib/python3.14/site-packages/fastapi/testclient.py:1
  /Users/louije/Development/gip/Autometa/.worktrees/multi-source-dashboards/.venv/lib/python3.14/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
5 passed, 92 deselected, 1 warning in 0.69s
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
