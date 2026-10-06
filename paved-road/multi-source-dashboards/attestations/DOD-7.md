# DOD-7

**Critère** — [décision 1 : déclaration explicite] Je déclare une déclinaison par le skill `update_dashboard` avec sa clé et son libellé, et je la retire de la même façon. Déclarer une clé déjà présente est refusé sans créer de doublon, même quand deux déclarations partent en même temps. Retirer une déclinaison supprime son fichier de données interne ; si une publication est active, le retrait annonce que le lien public reste en ligne jusqu'au prochain rafraîchissement.
**Commande** — `uv run --frozen pytest tests/test_variants_lib.py tests/test_dashboard_skill_scripts.py -k dod_7 -q`
**Code de sortie** — 0
**Sortie** — 

```
...............                                                          [100%]
15 passed, 24 deselected in 1.04s
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `198be3e0ca19c7344346b460f47632a7997c1a8b` |
| `lib` | `84a1e7d287295a59e01cb7c7538590bc2859cd10` |
| `scripts` | `1db5541ee291f83cc7f58352cd6e10d88881ebf6` |
| `skills` | `7b027d42d1f92f23e8e4d4564a145642ca751e07` |
| `alembic` | `4199ab20c8200527287a4d1328e495721ee59ab2` |
| `tests` | `ec3304b8db8c97656f9df8252c87a26ab455a11c` |
| `browser` | `3838fcc50ff5c25b4f975d5d2bdbc060a2ca9cca` |

**Verdict** — démontré.
