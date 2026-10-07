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
5 passed, 123 deselected, 1 warning in 1.19s
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `198be3e0ca19c7344346b460f47632a7997c1a8b` |
| `lib` | `857b7b5f0d013efe0b7a0a185fffe090db79d3a7` |
| `scripts` | `1db5541ee291f83cc7f58352cd6e10d88881ebf6` |
| `skills` | `c249e7699a8914d4f455daef4f8a468d8af21af6` |
| `alembic` | `4199ab20c8200527287a4d1328e495721ee59ab2` |
| `tests` | `0aa8b2c2bad0ad3775012775d4eba5752186eb87` |
| `browser` | `3838fcc50ff5c25b4f975d5d2bdbc060a2ca9cca` |

**Verdict** — démontré.
