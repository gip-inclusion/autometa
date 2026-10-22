# DOD-8

**Critère** — [du brief : « même principe que la documentation »] Si quelqu'un a modifié ou supprimé une macro dans Zendesk entre ma lecture de la proposition et mon approbation, cette macro est laissée telle quelle, elle m'est nommée avec la raison, et les autres sont modifiées normalement. Un simple changement de place dans la liste ne compte pas comme une modification.
**Commande** — `uv run --frozen pytest tests/test_zendesk_macros.py tests/test_zendesk.py -k dod_8_`
**Code de sortie** — 0
**Sortie** — 

```
============================= test session starts ==============================
platform linux -- Python 3.14.8, pytest-9.0.3, pluggy-1.6.0
rootdir: /home/yannick/work/itou/autometa
configfile: pytest.ini
plugins: cov-7.1.0, mock-3.15.1, playwright-0.9.0, base-url-2.1.0, anyio-4.13.0
collected 124 items / 119 deselected / 5 selected

tests/test_zendesk_macros.py .                                           [ 20%]
tests/test_zendesk.py ....                                               [100%]

====================== 5 passed, 119 deselected in 0.27s =======================
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
