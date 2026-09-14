# DOD-7

**Critère** — [décision 1 : déclaration explicite] Je déclare une déclinaison par le skill `update_dashboard` avec sa clé et son libellé, et je la retire de la même façon. Déclarer une clé déjà présente est refusé sans créer de doublon, même quand deux déclarations partent en même temps. Retirer une déclinaison supprime son fichier de données interne ; si une publication est active, le retrait annonce que le lien public reste en ligne jusqu'au prochain rafraîchissement.
**Commande** — `uv run --frozen pytest tests/test_variants_lib.py tests/test_dashboard_skill_scripts.py -k dod_7 -q`
**Code de sortie** — 0
**Sortie** — 

```
..........                                                               [100%]
10 passed, 15 deselected in 0.70s
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `fc7ea2412f4440b60688cde4af450c28a87036cf` |
| `lib` | `dc9847fa9b2068ea45fa108a5b65181732339298` |
| `scripts` | `a4d9138781a04d96661f9e8647f4867cf513d756` |
| `skills` | `7909438b122995b1a074b7e22d91284e5dc06587` |
| `alembic` | `9dbb4fa33c1a7f59f3d1f956aa23798333baebf3` |
| `tests` | `673cde27ace5f05aba230ca875362a9c3a4ea86e` |
| `browser` | `e84a913b0c4e492f80b0c69655b3d975df4f39bb` |

**Verdict** — démontré.
