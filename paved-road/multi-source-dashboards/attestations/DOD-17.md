# DOD-17

**Critère** — [lentille gap-hunter : archivage] Archiver un tableau multi-sources ne supprime aucune déclinaison : jetons et libellés sont conservés, et désarchiver rétablit les mêmes liens.
**Commande** — `uv run --frozen pytest tests/test_variants_lib.py -k dod_17 -q`
**Code de sortie** — 0
**Sortie** — 

```
..                                                                       [100%]
2 passed, 26 deselected in 0.71s
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
