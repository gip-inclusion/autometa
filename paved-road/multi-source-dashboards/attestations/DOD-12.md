# DOD-12

**Critère** — [lentille gap-hunter : entrée hors limites] La clé d'une déclinaison est faite de lettres minuscules, chiffres et tirets (1 à 64 caractères) et le libellé est obligatoire. Une clé vide, avec espaces ou caractères spéciaux, ou un libellé vide, est refusée en nommant le champ fautif, sans rien créer. Deux déclinaisons peuvent porter le même libellé : la clé reste l'identifiant, et elle s'affiche à côté du libellé sur la page d'édition et sur l'index interne.
**Commande** — `uv run --frozen pytest tests/test_variants_lib.py tests/test_dashboard_skill_scripts.py -k dod_12 -q`
**Code de sortie** — 0
**Sortie** — 

```
...........                                                              [100%]
11 passed, 22 deselected in 1.19s
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
