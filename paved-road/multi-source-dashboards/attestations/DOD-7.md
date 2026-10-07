# DOD-7

**Critère** — [décision 1 : déclaration explicite] Je déclare une déclinaison par le skill `update_dashboard` avec sa clé et son libellé, et je la retire de la même façon. Déclarer une clé déjà présente est refusé sans créer de doublon, même quand deux déclarations partent en même temps. Retirer une déclinaison supprime son fichier de données interne ; si une publication est active, le retrait annonce que le lien public reste en ligne jusqu'au prochain rafraîchissement.
**Commande** — `uv run --frozen pytest tests/test_variants_lib.py tests/test_dashboard_skill_scripts.py -k dod_7 -q`
**Code de sortie** — 0
**Sortie** — 

```
...............                                                          [100%]
15 passed, 30 deselected in 0.74s
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
