# DOD-1

**Critère** — Quand je demande une campagne, l'agent pose le cadrage (public, acte attendu, outil d'envoi, signataire) avant d'écrire. Si ma demande est vide ou contredit la carte de l'initiative, il s'arrête et me pose la question.
**Commande** — `uv run --frozen pytest tests/test_skill_campagne_email.py -k dod_1`
**Code de sortie** — 0
**Sortie** — 

```
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.0.3, pluggy-1.6.0
rootdir: C:\Users\MeHd1\AppData\Local\Temp\autometa-src\repo
configfile: pytest.ini
plugins: anyio-4.14.2, base-url-2.1.0, cov-7.1.0, mock-3.15.1, playwright-0.9.0, xdist-3.8.0
collected 5 items / 4 deselected / 1 selected

tests\test_skill_campagne_email.py .                                     [100%]

======================= 1 passed, 4 deselected in 0.67s =======================
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `b5981d730a7b042e097945fef56620e939c91be3` |
| `lib` | `0f12117502f8c368fae3a09205b986f72f800ac7` |
| `scripts` | `470cb030c847eb404087af2bd9e9d64bb64f1cec` |
| `skills` | `d4de5cc9a3d232036627cf2660e9604169b2442e` |
| `alembic` | `e47a5a9c077aa3bea1cf7e375cc511771b0a46c6` |
| `tests` | `77b9b9f8962bb505b77fcfa0b24aa58f473663a0` |
| `browser` | `6feb69d1ac52328908a2aff37de9bdfa4ed0be20` |

**Verdict** — démontré.
