# DOD-1

**Critère** — [du brief : « visiting …/?q=1234-… will ajax load the correct file »] Quand j'ouvre `/interactive/{slug}/?q={jeton}` avec le jeton d'une déclinaison déclarée, le tableau de bord affiche les données de cette seule déclinaison : son nom en en-tête, ses chiffres.
**Commande** — `uv run --frozen pytest browser/test_variants_page.py -k dod_1 -q`
**Code de sortie** — 0
**Sortie** — 

```
......                                                                   [100%]
6 passed, 4 deselected in 1.60s
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `fc7ea2412f4440b60688cde4af450c28a87036cf` |
| `lib` | `dc9847fa9b2068ea45fa108a5b65181732339298` |
| `scripts` | `a4d9138781a04d96661f9e8647f4867cf513d756` |
| `skills` | `7909438b122995b1a074b7e22d91284e5dc06587` |
| `alembic` | `9dbb4fa33c1a7f59f3d1f956aa23798333baebf3` |
| `tests` | `673cde27ace5f05aba230ca875362a9c3a4ea86e` |
| `browser` | `e84a913b0c4e492f80b0c69655b3d975df4f39bb` |

**Verdict** — démontré.
