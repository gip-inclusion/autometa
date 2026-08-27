# DOD-4

**Critère** — Quand le titre du rapport ne donne aucun nom de fichier lisible (titre vide, ou uniquement des caractères spéciaux), alors le fichier s'appelle `rapport-<numéro du rapport>.md`.
**Commande** — `uv run --frozen pytest tests/test_rapports.py -k dod_4 -q`
**Code de sortie** — 0
**Sortie** — 

```
..                                                                       [100%]
=============================== warnings summary ===============================
tests/test_rapports.py::test_dod_4_un_titre_sans_nom_lisible_se_replie_sur_le_numero[]
  /Users/cdarnis/worktrees/autometa/paved-road-rebuild/tests/conftest.py:132: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
2 passed, 16 deselected, 1 warning in 1.52s
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `ac984aa0d79cb453d0be902a4c1a76fff3ebcb7d` |
| `lib` | `9f1892b99831a160c3df2c64760d9113cd4f0bc4` |
| `scripts` | `e114399c96beb110374e4da34251fe8dc7946524` |
| `skills` | `9f8d3ff0d53a99287ac1099fceb033e152afe7e8` |
| `alembic` | `e9eb6695e7e6870bc8e50d352f8bc021d2d06ad7` |
| `tests` | `e5d1f6510769f14d11c013f357fb73be25be0561` |

**Verdict** — démontré.
