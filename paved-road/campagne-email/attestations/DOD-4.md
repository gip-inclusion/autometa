# DOD-4

**Critère** — La campagne prête se dépose dans la base Notion « Campagnes à valider », avec le statut « À valider ». Rien n'est programmé ni envoyé.
**Commande** — `uv run --frozen pytest tests/test_skill_campagne_email.py -k dod_4`
**Code de sortie** — 0
**Sortie** — 

```
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.0.3, pluggy-1.6.0
rootdir: C:\Users\MeHd1\AppData\Local\Temp\autometa-src\repo
configfile: pytest.ini
plugins: anyio-4.14.2, base-url-2.1.0, cov-7.1.0, mock-3.15.1, playwright-0.9.0, xdist-3.8.0
collected 11 items / 3 deselected / 8 selected

tests\test_skill_campagne_email.py ........                              [100%]

======================= 8 passed, 3 deselected in 0.61s =======================
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `f3071ed27c860a855acd4b7af397847ed368a29d` |
| `lib` | `0a667b580317898ee2280298b4cdaa8d092cb481` |
| `scripts` | `470cb030c847eb404087af2bd9e9d64bb64f1cec` |
| `skills` | `97c73a66d9c20ddd40da6d760f4f0b31c8d2082b` |
| `alembic` | `e47a5a9c077aa3bea1cf7e375cc511771b0a46c6` |
| `tests` | `ede713de4d69b0adb71065730230d7dce3d766fc` |
| `browser` | `6feb69d1ac52328908a2aff37de9bdfa4ed0be20` |

**Verdict** — démontré.
