# DOD-4

**Critère** — [du brief : « mapping between facet and uuid is stored in our work db »] Les déclinaisons d'un tableau de bord (clé, libellé, jeton) sont enregistrées en base. Le jeton est généré par l'outil, jamais choisi à la main, et reste le même d'un rafraîchissement à l'autre : un lien partagé continue de fonctionner après le passage du cron et après une republication.
**Commande** — `uv run --frozen pytest tests/test_variants_lib.py -k dod_4 -q`
**Code de sortie** — 0
**Sortie** — 

```
..                                                                       [100%]
2 passed, 17 deselected in 0.71s
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
