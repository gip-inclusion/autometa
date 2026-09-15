# DOD-2

**Critère** — [du brief : « not having a query string will soft-404 »] Sur la version publiée, sans `?q` ou avec un jeton inconnu, la page affiche un message « ce lien n'est pas valide », et aucune liste de déclinaisons, aucun sélecteur, aucun lien vers une autre déclinaison.
**Commande** — `uv run --frozen pytest browser/test_variants_page.py -k dod_2 -q`
**Code de sortie** — 0
**Sortie** — 

```
....                                                                     [100%]
4 passed, 6 deselected in 4.02s
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `14f1d267ea8f25600f6ffefbb9007e08ed3b567e` |
| `lib` | `b02675ca62f3ed96f13b7f8baa2f0848af28b7db` |
| `scripts` | `a4d9138781a04d96661f9e8647f4867cf513d756` |
| `skills` | `492f69b14d8d3ac205c8acf424a21a52ccef1e8a` |
| `alembic` | `9dbb4fa33c1a7f59f3d1f956aa23798333baebf3` |
| `tests` | `a2ca65a4637f982a263f66790c95d57aa57fdb62` |
| `browser` | `220f7cad51a41efbefd065e26af541c0f2cc5999` |

**Verdict** — démontré.
