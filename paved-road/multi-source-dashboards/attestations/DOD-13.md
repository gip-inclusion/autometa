# DOD-13

**Critère** — [lentille gap-hunter : valeur hors limites] La page valide la forme du jeton avant toute requête : un `?q` vide, qui n'a pas la forme d'un UUID, ou qui contient `/` ou `..`, affiche « ce lien n'est pas valide » sans qu'aucune requête ne parte. Révision 2026-10-02 — la forme valide d'un `?q` est celle d'une clé (lettres minuscules, chiffres et tirets, 1 à 64 caractères), qui couvre aussi un UUID ; vide, autre forme, `/` ou `..` : « ce lien n'est pas valide », sans requête. Motif : le jeton est la clé par défaut (DOD-4). Revalidé le 2026-10-02.
**Commande** — `uv run --frozen pytest browser/test_variants_page.py -k dod_13 -q`
**Code de sortie** — 0
**Sortie** — 

```
.....                                                                    [100%]
5 passed, 7 deselected in 1.59s
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
