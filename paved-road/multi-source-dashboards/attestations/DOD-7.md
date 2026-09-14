# DOD-7

**Critère** — [décision 1 : déclaration explicite] Je déclare une déclinaison par le skill `update_dashboard` avec sa clé et son libellé, et je la retire de la même façon. Déclarer une clé déjà présente est refusé sans créer de doublon, même quand deux déclarations partent en même temps. Retirer une déclinaison supprime son fichier de données interne ; si une publication est active, le retrait annonce que le lien public reste en ligne jusqu'au prochain rafraîchissement.
**Commande** — `uv run --frozen pytest tests/test_variants_lib.py tests/test_dashboard_skill_scripts.py -k dod_7 -q`
**Code de sortie** — 0
**Sortie** — 

```
.............                                                            [100%]
13 passed, 16 deselected in 0.90s
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `a9e9273de118212994ef9e90dda9465eeeb907c5` |
| `lib` | `b02675ca62f3ed96f13b7f8baa2f0848af28b7db` |
| `scripts` | `a4d9138781a04d96661f9e8647f4867cf513d756` |
| `skills` | `492f69b14d8d3ac205c8acf424a21a52ccef1e8a` |
| `alembic` | `9dbb4fa33c1a7f59f3d1f956aa23798333baebf3` |
| `tests` | `86afe6cce9a5bc608482aa89360d70a8abd9dfc9` |
| `browser` | `220f7cad51a41efbefd065e26af541c0f2cc5999` |

**Verdict** — démontré.
