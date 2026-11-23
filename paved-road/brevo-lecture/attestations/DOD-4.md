# DOD-4

**Critère** — Rien de ce qui sort de Brevo ne contient une adresse email. Un email envoyé sans modèle est compté par son objet, et un objet vu moins de cinq fois ne sort pas : il est compté avec les autres sur une seule ligne.
**Commande** — `uv run --frozen pytest tests/test_brevo.py -k dod_4`
**Code de sortie** — 0
**Sortie** — 

```
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.0.3, pluggy-1.6.0
rootdir: C:\Users\MeHd1\AppData\Local\Temp\autometa-src\repo
configfile: pytest.ini
plugins: anyio-4.14.2, base-url-2.1.0, cov-7.1.0, mock-3.15.1, playwright-0.9.0, xdist-3.8.0
collected 34 items / 28 deselected / 6 selected

tests\test_brevo.py ......                                               [100%]

====================== 6 passed, 28 deselected in 1.58s =======================
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `34922cdd4c93d37526506621a5166e5434c91fee` |
| `lib` | `6f9d35c0b959945d380484a25ae60a61adb3766f` |
| `scripts` | `470cb030c847eb404087af2bd9e9d64bb64f1cec` |
| `skills` | `9eccb87dae03f170bc63c73e9dea99ce804e0194` |
| `alembic` | `e47a5a9c077aa3bea1cf7e375cc511771b0a46c6` |
| `tests` | `76e6d42fdd0676358d523d6ce3b996caddbab88f` |
| `browser` | `6feb69d1ac52328908a2aff37de9bdfa4ed0be20` |

**Verdict** — démontré.
