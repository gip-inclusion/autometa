# DOD-15

**Critère** — [lentille gap-hunter : échec partiel] Quand le calcul d'une déclinaison échoue pendant le cron du gabarit, les autres sont produites quand même, le fichier précédent de celle qui a échoué est conservé, et le cron se termine en échec en nommant les clés fautives dans son historique.
**Commande** — `uv run --frozen pytest tests/test_multi_source_template.py tests/test_cron.py -k dod_15 -q`
**Code de sortie** — 0
**Sortie** — 

```
.....                                                                    [100%]
=============================== warnings summary ===============================
tests/test_cron.py::test_dod_15_a_partial_publication_run_still_refreshes
  /Users/louije/Development/gip/autometa-multi-source/tests/conftest.py:133: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
5 passed, 123 deselected, 1 warning in 1.20s
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `025f36cf58659e483324d1a6cfc73a6df9549b0a` |
| `lib` | `24dea1b178864a4e9d2d459702281b8dd5467486` |
| `scripts` | `1db5541ee291f83cc7f58352cd6e10d88881ebf6` |
| `skills` | `4cd9e2f4ac9726e2a7cfd34ece88e82aaea1f745` |
| `alembic` | `4199ab20c8200527287a4d1328e495721ee59ab2` |
| `tests` | `5b7ce2570650d81cd71ce8c342b44d048849b78f` |
| `browser` | `3838fcc50ff5c25b4f975d5d2bdbc060a2ca9cca` |

**Verdict** — démontré.
