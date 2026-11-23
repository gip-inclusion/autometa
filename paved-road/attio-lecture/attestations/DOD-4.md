# DOD-4

**Critère** — Ce qu'un tableau de bord lit dans Attio ne contient aucun email ni aucun téléphone.
**Commande** — `uv run --frozen pytest tests/test_attio.py -k dod_4`
**Code de sortie** — 0
**Sortie** — 

```
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.0.3, pluggy-1.6.0
rootdir: C:\Users\MeHd1\AppData\Local\Temp\autometa-src\wt-attio
configfile: pytest.ini
plugins: anyio-4.14.2, base-url-2.1.0, cov-7.1.0, mock-3.15.1, playwright-0.9.0, xdist-3.8.0
collected 56 items / 40 deselected / 16 selected

tests\test_attio.py ................                                     [100%]

====================== 16 passed, 40 deselected in 2.50s ======================
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `7c1a4e7a7586e7bfc286d13403edf27a83afa430` |
| `lib` | `aa104a25186e211a66c6f70d8c23f62615c965fa` |
| `scripts` | `470cb030c847eb404087af2bd9e9d64bb64f1cec` |
| `skills` | `d5d836ae958609ad8837909c057f97f248145e20` |
| `alembic` | `e47a5a9c077aa3bea1cf7e375cc511771b0a46c6` |
| `tests` | `6612580243f09a0e883ccbe58f72a0fc9363b5dc` |
| `browser` | `6feb69d1ac52328908a2aff37de9bdfa4ed0be20` |

**Verdict** — démontré.
