# DOD-9

**Critère** — [du brief : « first class citizen » ; « edit the skill »] Le skill `create_dashboard` propose un gabarit multi-sources (page qui lit `?q`, cron qui produit un fichier par déclinaison), et ses instructions demandent à l'agent de proposer ce mode quand une demande vise plusieurs territoires ou entités sur un même écran, et d'obtenir un accord explicite avant de l'utiliser. Ce critère porte sur des instructions en prose : il se vérifie à la lecture, pas par un test.
**Commande** — `uv run --frozen pytest tests/test_dashboards_lib.py tests/test_dashboard_skill_scripts.py -k dod_9 -q`
**Code de sortie** — 0
**Sortie** — 

```
...                                                                      [100%]
3 passed, 64 deselected in 0.69s
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `025f36cf58659e483324d1a6cfc73a6df9549b0a` |
| `lib` | `24dea1b178864a4e9d2d459702281b8dd5467486` |
| `scripts` | `1db5541ee291f83cc7f58352cd6e10d88881ebf6` |
| `skills` | `4cd9e2f4ac9726e2a7cfd34ece88e82aaea1f745` |
| `alembic` | `4199ab20c8200527287a4d1328e495721ee59ab2` |
| `tests` | `5b7ce2570650d81cd71ce8c342b44d048849b78f` |
| `browser` | `3838fcc50ff5c25b4f975d5d2bdbc060a2ca9cca` |

**Verdict** — démontré.
