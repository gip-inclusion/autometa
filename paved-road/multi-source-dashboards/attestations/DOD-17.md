# DOD-17

**Critère** — [lentille gap-hunter : archivage] Archiver un tableau multi-sources ne supprime aucune déclinaison : jetons et libellés sont conservés, et désarchiver rétablit les mêmes liens.
**Commande** — `uv run --frozen pytest tests/test_variants_lib.py -k dod_17 -q`
**Code de sortie** — 0
**Sortie** — 

```
..                                                                       [100%]
2 passed, 17 deselected in 0.68s
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
