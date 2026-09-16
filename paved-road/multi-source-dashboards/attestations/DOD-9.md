# DOD-9

**Critère** — [du brief : « first class citizen » ; « edit the skill »] Le skill `create_dashboard` propose un gabarit multi-sources (page qui lit `?q`, cron qui produit un fichier par déclinaison), et ses instructions demandent à l'agent de proposer ce mode quand une demande vise plusieurs territoires ou entités sur un même écran, et d'obtenir un accord explicite avant de l'utiliser. Ce critère porte sur des instructions en prose : il se vérifie à la lecture, pas par un test.
**Commande** — `uv run --frozen pytest tests/test_dashboards_lib.py tests/test_dashboard_skill_scripts.py -k dod_9 -q`
**Code de sortie** — 0
**Sortie** — 

```
...                                                                      [100%]
3 passed, 56 deselected in 0.79s
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `58b365eef7b9b035d9f68480c1d172f91e42fc07` |
| `lib` | `a7a421f061a11f05aaf02377b9c935640a68aa07` |
| `scripts` | `a4d9138781a04d96661f9e8647f4867cf513d756` |
| `skills` | `e1ac5c036de0d232af9c3e9fcdf21643e7ce045e` |
| `alembic` | `9dbb4fa33c1a7f59f3d1f956aa23798333baebf3` |
| `tests` | `7649e1e844a14ed0481e8aa963d4c2414bbe0854` |
| `browser` | `237931537134f569ff3228a21f44d3542707d581` |

**Verdict** — démontré.
