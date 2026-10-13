# DOD-12

**Critère** — [lentille gap-hunter : entrée hors limites] La clé d'une déclinaison est faite de lettres minuscules, chiffres et tirets (1 à 64 caractères) et le libellé est obligatoire. Une clé vide, avec espaces ou caractères spéciaux, ou un libellé vide, est refusée en nommant le champ fautif, sans rien créer. Deux déclinaisons peuvent porter le même libellé : la clé reste l'identifiant, et elle s'affiche à côté du libellé sur la page d'édition et sur l'index interne.
**Commande** — `uv run --frozen pytest tests/test_variants_lib.py tests/test_dashboard_skill_scripts.py -k dod_12 -q`
**Code de sortie** — 0
**Sortie** — 

```
...........                                                              [100%]
11 passed, 39 deselected in 1.01s
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `025f36cf58659e483324d1a6cfc73a6df9549b0a` |
| `lib` | `24dea1b178864a4e9d2d459702281b8dd5467486` |
| `scripts` | `1db5541ee291f83cc7f58352cd6e10d88881ebf6` |
| `skills` | `4cd9e2f4ac9726e2a7cfd34ece88e82aaea1f745` |
| `alembic` | `4199ab20c8200527287a4d1328e495721ee59ab2` |
| `tests` | `5b7ce2570650d81cd71ce8c342b44d048849b78f` |
| `browser` | `3838fcc50ff5c25b4f975d5d2bdbc060a2ca9cca` |

**Verdict** — démontré.
