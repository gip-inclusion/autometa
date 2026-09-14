# DOD-9

**Critère** — [du brief : « first class citizen » ; « edit the skill »] Le skill `create_dashboard` propose un gabarit multi-sources (page qui lit `?q`, cron qui produit un fichier par déclinaison), et ses instructions demandent à l'agent de proposer ce mode quand une demande vise plusieurs territoires ou entités sur un même écran, et d'obtenir un accord explicite avant de l'utiliser. Ce critère porte sur des instructions en prose : il se vérifie à la lecture, pas par un test.
**Commande** — `uv run --frozen pytest tests/test_dashboards_lib.py tests/test_dashboard_skill_scripts.py -k dod_9 -q`
**Code de sortie** — 0
**Sortie** — 

```
...                                                                      [100%]
3 passed, 53 deselected in 0.66s
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `22e7f8897e3cc5fd322aef80ffaacbebf57705b1` |
| `lib` | `b02675ca62f3ed96f13b7f8baa2f0848af28b7db` |
| `scripts` | `a4d9138781a04d96661f9e8647f4867cf513d756` |
| `skills` | `492f69b14d8d3ac205c8acf424a21a52ccef1e8a` |
| `alembic` | `9dbb4fa33c1a7f59f3d1f956aa23798333baebf3` |
| `tests` | `0c1437442bfac189ccc90e7aabcdf3210534fda2` |
| `browser` | `e84a913b0c4e492f80b0c69655b3d975df4f39bb` |

**Verdict** — démontré.
