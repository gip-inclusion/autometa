# DOD-5

**Critère** — Les liens déjà partagés vers la « version exportable » d'un rapport continuent de mener à ce rapport.
**Commande** — `uv run --frozen pytest tests/test_rapports.py -k dod_5 -q`
**Code de sortie** — 0
**Sortie** — 

```
.                                                                        [100%]
=============================== warnings summary ===============================
tests/test_rapports.py::test_dod_5_les_liens_deja_partages_menent_toujours_au_rapport
  /Users/cdarnis/worktrees/autometa/paved-road-rebuild/tests/conftest.py:132: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
1 passed, 17 deselected, 1 warning in 1.42s
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `ac984aa0d79cb453d0be902a4c1a76fff3ebcb7d` |
| `lib` | `9f1892b99831a160c3df2c64760d9113cd4f0bc4` |
| `scripts` | `d02be732547319b0fe39f1c279266c85d49dbb4c` |
| `skills` | `9f8d3ff0d53a99287ac1099fceb033e152afe7e8` |
| `alembic` | `e9eb6695e7e6870bc8e50d352f8bc021d2d06ad7` |
| `tests` | `e5d1f6510769f14d11c013f357fb73be25be0561` |

**Verdict** — démontré.
