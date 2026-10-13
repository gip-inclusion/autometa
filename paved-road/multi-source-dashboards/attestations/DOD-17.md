# DOD-17

**Critère** — [lentille gap-hunter : archivage] Archiver un tableau multi-sources ne supprime aucune déclinaison : jetons et libellés sont conservés, et désarchiver rétablit les mêmes liens.
**Commande** — `uv run --frozen pytest tests/test_variants_lib.py -k dod_17 -q`
**Code de sortie** — 0
**Sortie** — 

```
..                                                                       [100%]
2 passed, 27 deselected in 0.79s
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
