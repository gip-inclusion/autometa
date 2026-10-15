# DOD-3

**Critère** — [du brief : « éditer … en batch », « même principe que la documentation »] Quand je demande de remplacer un mot ou une expression dans les macros, Autometa me présente la liste des macros qui changeraient, inactives comprises, avec pour chacune ce qui est retiré et ce qui est ajouté, montré au niveau du paragraphe modifié et non de la réponse entière, et rien n'est encore modifié dans Zendesk. Le remplacement porte sur le titre, la description, le sujet et le texte de réponse.
**Commande** — `uv run --frozen pytest tests/test_zendesk_macros.py tests/test_zendesk.py -k dod_3_`
**Code de sortie** — 0
**Sortie** — 

```
============================= test session starts ==============================
platform linux -- Python 3.14.8, pytest-9.0.3, pluggy-1.6.0
rootdir: /home/yannick/work/itou/autometa
configfile: pytest.ini
plugins: cov-7.1.0, mock-3.15.1, playwright-0.9.0, base-url-2.1.0, anyio-4.13.0
collected 124 items / 122 deselected / 2 selected

tests/test_zendesk_macros.py ..                                          [100%]

====================== 2 passed, 122 deselected in 0.24s =======================
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
