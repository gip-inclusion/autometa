# DOD-1

**Critère** — [du brief : « visiting …/?q=1234-… will ajax load the correct file »] Quand j'ouvre `/interactive/{slug}/?q={jeton}` avec le jeton d'une déclinaison déclarée, le tableau de bord affiche les données de cette seule déclinaison : son nom en en-tête, ses chiffres.
**Commande** — `uv run --frozen pytest browser/test_variants_page.py -k dod_1 -q`
**Code de sortie** — 0
**Sortie** — 

```
........                                                                 [100%]
8 passed, 4 deselected in 2.74s
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
