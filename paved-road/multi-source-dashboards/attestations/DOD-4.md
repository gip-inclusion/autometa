# DOD-4

**Critère** — [du brief : « mapping between facet and uuid is stored in our work db »] Les déclinaisons d'un tableau de bord (clé, libellé, jeton) sont enregistrées en base. Le jeton est généré par l'outil, jamais choisi à la main, et reste le même d'un rafraîchissement à l'autre : un lien partagé continue de fonctionner après le passage du cron et après une republication. Révision 2026-10-02 — par défaut, le jeton d'une déclinaison est sa clé (`?q=78`, `data/78.json`) ; il est un UUID généré par l'outil seulement quand le tableau le demande (`update_dashboard --obfuscate-variants`), et alors pour toutes ses déclinaisons. Changer ce mode sur un tableau qui a déjà des déclinaisons est refusé : les liens partagés casseraient. Le jeton reste stable dans les deux modes. Motif : un nom de fichier lisible suffit tant que le lien n'a pas à être secret. Revalidé le 2026-10-02.
**Commande** — `uv run --frozen pytest tests/test_variants_lib.py tests/test_dashboard_skill_scripts.py -k dod_4 -q`
**Code de sortie** — 0
**Sortie** — 

```
.......                                                                  [100%]
7 passed, 32 deselected in 0.85s
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
