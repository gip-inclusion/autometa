# DOD-1

**Critère** — Un tableau de bord liste les modèles d'email d'un compte Brevo, avec leur nom, leur objet et leur état, actif ou non.
**Commande** — `uv run --frozen pytest tests/test_brevo.py -k dod_1`
**Code de sortie** — 0
**Sortie** — 

```
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.0.3, pluggy-1.6.0
rootdir: C:\Users\MeHd1\AppData\Local\Temp\autometa-src\wt-brevo
configfile: pytest.ini
plugins: anyio-4.14.2, base-url-2.1.0, cov-7.1.0, mock-3.15.1, playwright-0.9.0, xdist-3.8.0
collected 42 items / 36 deselected / 6 selected

tests\test_brevo.py ......                                               [100%]

============================== warnings summary ===============================
.venv\Lib\site-packages\fastapi\testclient.py:1
  C:\Users\MeHd1\AppData\Local\Temp\autometa-src\wt-brevo\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
================= 6 passed, 36 deselected, 1 warning in 1.66s =================
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `34922cdd4c93d37526506621a5166e5434c91fee` |
| `lib` | `a6245954a730ab72471860788c95322fa08b5995` |
| `scripts` | `470cb030c847eb404087af2bd9e9d64bb64f1cec` |
| `skills` | `ff7c7b8393e7ac227b39d91ba237f82eca4d2433` |
| `alembic` | `e47a5a9c077aa3bea1cf7e375cc511771b0a46c6` |
| `tests` | `e60ecaec01180f94d0f1cb711ca0427f80224c9f` |
| `browser` | `6feb69d1ac52328908a2aff37de9bdfa4ed0be20` |

**Verdict** — démontré.
