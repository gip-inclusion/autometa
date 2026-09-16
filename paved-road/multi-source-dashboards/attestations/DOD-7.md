# DOD-7

**Critère** — [décision 1 : déclaration explicite] Je déclare une déclinaison par le skill `update_dashboard` avec sa clé et son libellé, et je la retire de la même façon. Déclarer une clé déjà présente est refusé sans créer de doublon, même quand deux déclarations partent en même temps. Retirer une déclinaison supprime son fichier de données interne ; si une publication est active, le retrait annonce que le lien public reste en ligne jusqu'au prochain rafraîchissement.
**Commande** — `uv run --frozen pytest tests/test_variants_lib.py tests/test_dashboard_skill_scripts.py -k dod_7 -q`
**Code de sortie** — 0
**Sortie** — 

```
...............                                                          [100%]
15 passed, 18 deselected in 0.83s
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
