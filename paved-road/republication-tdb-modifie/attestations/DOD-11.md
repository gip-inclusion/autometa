# DOD-11

**Critère** — [Révision 2026-10-20, garde-fou de DOD-10] Cette alerte de conversation n'apparaît que lorsqu'il y a lieu : une conversation sans tableau publié, ou dont le tableau en ligne est déjà à jour, n'affiche aucune alerte.
**Commande** — `uv run --frozen pytest tests/test_conversation_dashboards.py::test_dod_11_conversation_sans_tableau_publie_ou_a_jour_ne_signale_rien -q`
**Code de sortie** — 0
**Sortie** — 

```
..                                                                       [100%]
=============================== warnings summary ===============================
tests/test_conversation_dashboards.py::test_dod_11_conversation_sans_tableau_publie_ou_a_jour_ne_signale_rien[no_publication]
  /home/lelia/Documents/PDI/Matometa/tests/conftest.py:134: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
2 passed, 1 warning in 1.63s
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `6949c9050c5a9d761c917f934bc190b050ebe6c6` |
| `lib` | `21e46bf4b524e6939ccf7a080591643bd9c5b683` |
| `scripts` | `292a403984c75249c2c2f0fdf5ab4fea8e0fbf98` |
| `skills` | `a17f23d627a1c18cf4a0ecd1f42d501d4667ea5d` |
| `alembic` | `4199ab20c8200527287a4d1328e495721ee59ab2` |
| `tests` | `9cb5eb29d7c02ef5d91866487eebcde62d98e85b` |
| `browser` | `0e22d10d4a1fbd411bc5db77ba166e82f28a7421` |

**Verdict** — démontré.
