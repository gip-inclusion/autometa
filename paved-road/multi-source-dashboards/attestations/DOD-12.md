# DOD-12

**Critère** — [lentille gap-hunter : entrée hors limites] La clé d'une déclinaison est faite de lettres minuscules, chiffres et tirets (1 à 64 caractères) et le libellé est obligatoire. Une clé vide, avec espaces ou caractères spéciaux, ou un libellé vide, est refusée en nommant le champ fautif, sans rien créer. Deux déclinaisons peuvent porter le même libellé : la clé reste l'identifiant, et elle s'affiche à côté du libellé sur la page d'édition et sur l'index interne.
**Commande** — `uv run --frozen pytest tests/test_variants_lib.py tests/test_dashboard_skill_scripts.py -k dod_12 -q`
**Code de sortie** — 0
**Sortie** — 

```
...........                                                              [100%]
11 passed, 34 deselected in 0.76s
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
