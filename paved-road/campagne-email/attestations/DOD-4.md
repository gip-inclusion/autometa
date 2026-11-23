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
collected 8 items / 6 deselected / 2 selected

tests\test_skill_campagne_email.py ..                                    [100%]

======================= 2 passed, 6 deselected in 0.55s =======================
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `b5981d730a7b042e097945fef56620e939c91be3` |
| `lib` | `0f12117502f8c368fae3a09205b986f72f800ac7` |
| `scripts` | `470cb030c847eb404087af2bd9e9d64bb64f1cec` |
| `skills` | `c079290073c98d184aaace75798797c4b21d7f31` |
| `alembic` | `e47a5a9c077aa3bea1cf7e375cc511771b0a46c6` |
| `tests` | `b3c63c9b0823eefcedd5a7f600b020ef964abc9e` |
| `browser` | `6feb69d1ac52328908a2aff37de9bdfa4ed0be20` |

**Verdict** — démontré.
