# DOD-9

**Critère** — [du brief : « first class citizen » ; « edit the skill »] Le skill `create_dashboard` propose un gabarit multi-sources (page qui lit `?q`, cron qui produit un fichier par déclinaison), et ses instructions demandent à l'agent de proposer ce mode quand une demande vise plusieurs territoires ou entités sur un même écran, et d'obtenir un accord explicite avant de l'utiliser. Ce critère porte sur des instructions en prose : il se vérifie à la lecture, pas par un test.
**Commande** — `uv run --frozen pytest tests/test_dashboards_lib.py tests/test_dashboard_skill_scripts.py -k dod_9 -q`
**Code de sortie** — 0
**Sortie** — 

```
...                                                                      [100%]
3 passed, 64 deselected in 0.70s
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `025f36cf58659e483324d1a6cfc73a6df9549b0a` |
| `lib` | `857b7b5f0d013efe0b7a0a185fffe090db79d3a7` |
| `scripts` | `1db5541ee291f83cc7f58352cd6e10d88881ebf6` |
| `skills` | `4cd9e2f4ac9726e2a7cfd34ece88e82aaea1f745` |
| `alembic` | `4199ab20c8200527287a4d1328e495721ee59ab2` |
| `tests` | `5e5459c774ff6e8e55e094e1d678b509109e3517` |
| `browser` | `3838fcc50ff5c25b4f975d5d2bdbc060a2ca9cca` |

**Verdict** — démontré.
