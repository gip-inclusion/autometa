# DOD-13

**Critère** — [lentille gap-hunter : valeur hors limites] La page valide la forme du jeton avant toute requête : un `?q` vide, qui n'a pas la forme d'un UUID, ou qui contient `/` ou `..`, affiche « ce lien n'est pas valide » sans qu'aucune requête ne parte.
**Commande** — `uv run --frozen pytest browser/test_variants_page.py -k dod_13 -q`
**Code de sortie** — 0
**Sortie** — 

```
...                                                                      [100%]
3 passed, 7 deselected in 3.78s
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
