# DOD-5

**Critère** — Une demande d'écriture, ou une lecture que le connecteur ne prévoit pas, est refusée avant tout appel à Attio, avec un message qui dit ce qui est permis.
**Commande** — `uv run --frozen pytest tests/test_attio.py -k dod_5`
**Code de sortie** — 0
**Sortie** — 

```
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.0.3, pluggy-1.6.0
rootdir: C:\Users\MeHd1\AppData\Local\Temp\autometa-src\wt-attio
configfile: pytest.ini
plugins: anyio-4.14.2, base-url-2.1.0, cov-7.1.0, mock-3.15.1, playwright-0.9.0, xdist-3.8.0
collected 69 items / 45 deselected / 24 selected

tests\test_attio.py ........................                             [100%]

====================== 24 passed, 45 deselected in 1.26s ======================
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `0530e45cf0cd563cdb30d2b30f77ecd1d25b8098` |
| `lib` | `da99825e400fd7b2b48baa725acdf133cb27c62b` |
| `scripts` | `470cb030c847eb404087af2bd9e9d64bb64f1cec` |
| `skills` | `68e90d1b5d80f347e7f31eb191a5978bb626cca8` |
| `alembic` | `e47a5a9c077aa3bea1cf7e375cc511771b0a46c6` |
| `tests` | `ebb457e9db60989ad33ab284ce645353f8d76cc8` |
| `browser` | `6feb69d1ac52328908a2aff37de9bdfa4ed0be20` |

**Verdict** — démontré.
