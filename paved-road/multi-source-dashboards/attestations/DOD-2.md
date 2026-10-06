# DOD-2

**Critère** — [du brief : « not having a query string will soft-404 »] Sur la version publiée, sans `?q` ou avec un jeton inconnu, la page affiche un message « ce lien n'est pas valide », et aucune liste de déclinaisons, aucun sélecteur, aucun lien vers une autre déclinaison.
**Commande** — `uv run --frozen pytest browser/test_variants_page.py -k dod_2 -q`
**Code de sortie** — 0
**Sortie** — 

```
....                                                                     [100%]
4 passed, 8 deselected in 2.03s
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
