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
collected 21 items / 19 deselected / 2 selected

tests\test_brevo.py ..                                                   [100%]

====================== 2 passed, 19 deselected in 2.11s =======================
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `bb56be70ee4febaa76bbd4176b8539b6101d4352` |
| `lib` | `c3b585d4e23609ee7c907a36b31bf1229527b5bb` |
| `scripts` | `470cb030c847eb404087af2bd9e9d64bb64f1cec` |
| `skills` | `e8481c727621d337545c4d8d3512b76e41556573` |
| `alembic` | `e47a5a9c077aa3bea1cf7e375cc511771b0a46c6` |
| `tests` | `626d668276eb37b2416035bc9cbe1149e75136ae` |
| `browser` | `6feb69d1ac52328908a2aff37de9bdfa4ed0be20` |

**Verdict** — démontré.
