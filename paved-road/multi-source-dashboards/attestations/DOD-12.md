# DOD-12

**Critère** — [lentille gap-hunter : entrée hors limites] La clé d'une déclinaison est faite de lettres minuscules, chiffres et tirets (1 à 64 caractères) et le libellé est obligatoire. Une clé vide, avec espaces ou caractères spéciaux, ou un libellé vide, est refusée en nommant le champ fautif, sans rien créer. Deux déclinaisons peuvent porter le même libellé : la clé reste l'identifiant, et elle s'affiche à côté du libellé sur la page d'édition et sur l'index interne.
**Commande** — `uv run --frozen pytest tests/test_variants_lib.py tests/test_dashboard_skill_scripts.py -k dod_12 -q`
**Code de sortie** — 0
**Sortie** — 

```
...........                                                              [100%]
11 passed, 38 deselected in 0.74s
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `025f36cf58659e483324d1a6cfc73a6df9549b0a` |
| `lib` | `857b7b5f0d013efe0b7a0a185fffe090db79d3a7` |
| `scripts` | `1db5541ee291f83cc7f58352cd6e10d88881ebf6` |
| `skills` | `4cd9e2f4ac9726e2a7cfd34ece88e82aaea1f745` |
| `alembic` | `4199ab20c8200527287a4d1328e495721ee59ab2` |
| `tests` | `5e5459c774ff6e8e55e094e1d678b509109e3517` |
| `browser` | `3838fcc50ff5c25b4f975d5d2bdbc060a2ca9cca` |

**Verdict** — démontré.
