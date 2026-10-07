# DOD-9

**Critère** — [du brief : « first class citizen » ; « edit the skill »] Le skill `create_dashboard` propose un gabarit multi-sources (page qui lit `?q`, cron qui produit un fichier par déclinaison), et ses instructions demandent à l'agent de proposer ce mode quand une demande vise plusieurs territoires ou entités sur un même écran, et d'obtenir un accord explicite avant de l'utiliser. Ce critère porte sur des instructions en prose : il se vérifie à la lecture, pas par un test.
**Commande** — `uv run --frozen pytest tests/test_dashboards_lib.py tests/test_dashboard_skill_scripts.py -k dod_9 -q`
**Code de sortie** — 0
**Sortie** — 

```
...                                                                      [100%]
3 passed, 60 deselected in 0.71s
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `198be3e0ca19c7344346b460f47632a7997c1a8b` |
| `lib` | `857b7b5f0d013efe0b7a0a185fffe090db79d3a7` |
| `scripts` | `1db5541ee291f83cc7f58352cd6e10d88881ebf6` |
| `skills` | `c249e7699a8914d4f455daef4f8a468d8af21af6` |
| `alembic` | `4199ab20c8200527287a4d1328e495721ee59ab2` |
| `tests` | `0aa8b2c2bad0ad3775012775d4eba5752186eb87` |
| `browser` | `3838fcc50ff5c25b4f975d5d2bdbc060a2ca9cca` |

**Verdict** — démontré.
