# DOD-10

**Critère** — [condition de sûreté du lien] La copie publiée d'un tableau multi-sources ne contient aucun fichier qui énumère les déclinaisons ou leurs jetons, et le tableau ne transmet pas le jeton aux sites externes qu'il lie (pas de referrer sortant).
**Commande** — `uv run --frozen pytest tests/test_multi_source_template.py -k dod_10 -q`
**Code de sortie** — 0
**Sortie** — 

```
.                                                                        [100%]
1 passed, 5 deselected in 0.55s
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
