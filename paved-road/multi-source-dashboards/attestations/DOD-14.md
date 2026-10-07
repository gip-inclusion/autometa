# DOD-14

**Critère** — [lentille gap-hunter : état absent] Jeton valide mais fichier de données absent : la page affiche « les données de cette déclinaison ne sont pas encore disponibles », message distinct du lien invalide, et la page d'édition marque la déclinaison « sans données ».
**Commande** — `uv run --frozen pytest tests/test_dashboards_routes.py browser/test_variants_page.py -k dod_14 -q`
**Code de sortie** — 0
**Sortie** — 

```
..                                                                       [100%]
=============================== warnings summary ===============================
tests/test_dashboards_routes.py::test_dod_14_detail_flags_a_variant_whose_data_file_is_missing
  /Users/louije/Development/gip/autometa-multi-source/tests/conftest.py:133: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
2 passed, 94 deselected, 1 warning in 1.95s
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `025f36cf58659e483324d1a6cfc73a6df9549b0a` |
| `lib` | `857b7b5f0d013efe0b7a0a185fffe090db79d3a7` |
| `scripts` | `1db5541ee291f83cc7f58352cd6e10d88881ebf6` |
| `skills` | `4cd9e2f4ac9726e2a7cfd34ece88e82aaea1f745` |
| `alembic` | `4199ab20c8200527287a4d1328e495721ee59ab2` |
| `tests` | `5e5459c774ff6e8e55e094e1d678b509109e3517` |
| `browser` | `3838fcc50ff5c25b4f975d5d2bdbc060a2ca9cca` |

**Verdict** — démontré.
