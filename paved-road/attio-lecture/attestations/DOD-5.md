# DOD-5

**Critère** — Une demande d'écriture, ou une lecture que le connecteur ne prévoit pas, est refusée avant tout appel à Attio, avec un message qui dit ce qui est permis.
**Commande** — `uv run --frozen pytest tests/test_attio.py -k dod_5`
**Code de sortie** — 0
**Sortie** — 

```
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.0.3, pluggy-1.6.0
rootdir: C:\Users\MeHd1\AppData\Local\Temp\autometa-src\repo
configfile: pytest.ini
plugins: anyio-4.14.2, base-url-2.1.0, cov-7.1.0, mock-3.15.1, playwright-0.9.0, xdist-3.8.0
collected 47 items / 26 deselected / 21 selected

tests\test_attio.py .....................                                [100%]

====================== 21 passed, 26 deselected in 1.45s ======================
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `7c1a4e7a7586e7bfc286d13403edf27a83afa430` |
| `lib` | `9b885eb98a66fd06b60e7032a5c3fb41f264f267` |
| `scripts` | `470cb030c847eb404087af2bd9e9d64bb64f1cec` |
| `skills` | `ffc021457d070352a69383758c4e80a223ace476` |
| `alembic` | `e47a5a9c077aa3bea1cf7e375cc511771b0a46c6` |
| `tests` | `2eacad17c5491e50321b4a96a817f92d1fac62e9` |
| `browser` | `6feb69d1ac52328908a2aff37de9bdfa4ed0be20` |

**Verdict** — démontré.
