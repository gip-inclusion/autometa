# DOD-4

**Critère** — [du brief : « mapping between facet and uuid is stored in our work db »] Les déclinaisons d'un tableau de bord (clé, libellé, jeton) sont enregistrées en base. Le jeton est généré par l'outil, jamais choisi à la main, et reste le même d'un rafraîchissement à l'autre : un lien partagé continue de fonctionner après le passage du cron et après une republication.
**Commande** — `uv run --frozen pytest tests/test_variants_lib.py -k dod_4 -q`
**Code de sortie** — 0
**Sortie** — 

```
..                                                                       [100%]
2 passed, 14 deselected in 0.79s
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
