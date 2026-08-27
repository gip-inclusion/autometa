# DOD-1

**Critère** — Quand je clique sur « Télécharger en Markdown » depuis un rapport, alors un fichier se télécharge, au lieu de s'afficher dans un onglet.
**Commande** — `uv run --frozen pytest tests/test_rapports.py -k dod_1 -q`
**Code de sortie** — 0
**Sortie** — 

```
.                                                                        [100%]
=============================== warnings summary ===============================
tests/test_rapports.py::test_dod_1_le_rapport_se_telecharge_au_lieu_de_s_afficher
  /Users/cdarnis/worktrees/autometa/paved-road-rebuild/tests/conftest.py:132: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
1 passed, 17 deselected, 1 warning in 3.45s
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
