# DOD-5

**Critère** — [du brief : « éditer … individuellement »] Quand je donne l'adresse d'une macro et une retouche à y faire, Autometa me montre la modification exacte sur cette macro seule, sans toucher aux autres.
**Commande** — `uv run --frozen pytest tests/test_zendesk_macros.py tests/test_zendesk.py -k dod_5_`
**Code de sortie** — 0
**Sortie** — 

```
============================= test session starts ==============================
platform darwin -- Python 3.14.6, pytest-9.0.3, pluggy-1.6.0
rootdir: /Users/louije/Development/gip/Autometa
configfile: pytest.ini
plugins: mock-3.15.1, cov-7.1.0, playwright-0.9.0, xdist-3.8.0, base-url-2.1.0, anyio-4.13.0
collected 116 items / 113 deselected / 3 selected

tests/test_zendesk_macros.py ...                                         [100%]

====================== 3 passed, 113 deselected in 0.23s =======================
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `b7391855da3bbea4c00cb70de11b61d485cc85a2` |
| `lib` | `9f7ed7fa3214535fcb9a6568b737e2579b2f7808` |
| `scripts` | `1db5541ee291f83cc7f58352cd6e10d88881ebf6` |
| `skills` | `36ae3d5414a51e5371fabf7e9f9d50ab4601ef9e` |
| `alembic` | `16587a72a81f00cbce480dac027c318a1a0e28f5` |
| `tests` | `eb76c0695bb8db958fe2c75ce6c57b57d2ae1918` |
| `browser` | `950c17e55519f3edc196b8d02673c268eb2932c0` |

**Verdict** — démontré.
