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
collected 23 items / 17 deselected / 6 selected

tests\test_attio.py ......                                               [100%]

====================== 6 passed, 17 deselected in 1.82s =======================
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `60bb69fd0ae88dce3093772bb604f6a963aa277b` |
| `lib` | `bf477d04ecc71b578e8085f05e9134357609436b` |
| `scripts` | `470cb030c847eb404087af2bd9e9d64bb64f1cec` |
| `skills` | `10e5b016d915c3ea38d2565ba5aebb4ddec77293` |
| `alembic` | `e47a5a9c077aa3bea1cf7e375cc511771b0a46c6` |
| `tests` | `8b755f1e00a57651ff734c48f5e2132fe968cac2` |
| `browser` | `6feb69d1ac52328908a2aff37de9bdfa4ed0be20` |

**Verdict** — démontré.
