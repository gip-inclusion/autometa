# DOD-2

**Critère** — Quand je demande à l'agent de retrouver des structures ou des contacts selon un critère (type, département, source), il rend la liste lue dans Attio, 500 enregistrements au plus.
**Commande** — `uv run --frozen pytest tests/test_attio.py -k dod_2`
**Code de sortie** — 0
**Sortie** — 

```
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.0.3, pluggy-1.6.0
rootdir: C:\Users\MeHd1\AppData\Local\Temp\autometa-src\repo
configfile: pytest.ini
plugins: anyio-4.14.2, base-url-2.1.0, cov-7.1.0, mock-3.15.1, playwright-0.9.0, xdist-3.8.0
collected 45 items / 42 deselected / 3 selected

tests\test_attio.py ...                                                  [100%]

====================== 3 passed, 42 deselected in 1.43s =======================
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `7c1a4e7a7586e7bfc286d13403edf27a83afa430` |
| `lib` | `425fb5da49e750d8afbedeb7127b386b9f66824c` |
| `scripts` | `470cb030c847eb404087af2bd9e9d64bb64f1cec` |
| `skills` | `df146602635d0102a6e75c6df106f0ec83f235ea` |
| `alembic` | `e47a5a9c077aa3bea1cf7e375cc511771b0a46c6` |
| `tests` | `57e10bc89f178fa34d35326088b3421fe9fed368` |
| `browser` | `6feb69d1ac52328908a2aff37de9bdfa4ed0be20` |

**Verdict** — démontré.
