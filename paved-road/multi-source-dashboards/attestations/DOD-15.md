# DOD-15

**Critère** — [lentille gap-hunter : échec partiel] Quand le calcul d'une déclinaison échoue pendant le cron du gabarit, les autres sont produites quand même, le fichier précédent de celle qui a échoué est conservé, et le cron se termine en échec en nommant les clés fautives dans son historique.
**Commande** — `uv run --frozen pytest tests/test_multi_source_template.py tests/test_cron.py -k dod_15 -q`
**Code de sortie** — 0
**Sortie** — 

```
.....                                                                    [100%]
=============================== warnings summary ===============================
tests/test_cron.py::test_dod_15_a_partial_publication_run_still_refreshes
  /Users/louije/Development/gip/Autometa/.worktrees/multi-source-dashboards/tests/conftest.py:133: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
5 passed, 114 deselected, 1 warning in 1.11s
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
