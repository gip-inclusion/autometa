# DOD-13

**Critère** — Quand l'adresse ou l'identifiant que je donne ne désigne pas une macro (article de l'aide, macro supprimée, identifiant inconnu), Autometa me le dit et ne crée aucune proposition ; il ne devine pas une macro voisine.
**Commande** — `uv run --frozen pytest tests/test_zendesk_macros.py tests/test_zendesk.py -k dod_13_`
**Code de sortie** — 0
**Sortie** — 

```
============================= test session starts ==============================
platform linux -- Python 3.14.8, pytest-9.0.3, pluggy-1.6.0
rootdir: /home/yannick/work/itou/autometa
configfile: pytest.ini
plugins: cov-7.1.0, mock-3.15.1, playwright-0.9.0, base-url-2.1.0, anyio-4.13.0
collected 124 items / 116 deselected / 8 selected

tests/test_zendesk.py ........                                           [100%]

====================== 8 passed, 116 deselected in 0.25s =======================
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `025f36cf58659e483324d1a6cfc73a6df9549b0a` |
| `lib` | `2b466b0abc4699b2de0eb914fd7580ef49d5c9be` |
| `scripts` | `1db5541ee291f83cc7f58352cd6e10d88881ebf6` |
| `skills` | `631a31cf0b909e7d79879f83c83dc383add9aa5a` |
| `alembic` | `4199ab20c8200527287a4d1328e495721ee59ab2` |
| `tests` | `172f90e291036b1318c23c94d3d2456d4afca77a` |
| `browser` | `3838fcc50ff5c25b4f975d5d2bdbc060a2ca9cca` |

**Verdict** — démontré.
