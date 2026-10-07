# DOD-4

**Critère** — [du brief : « mapping between facet and uuid is stored in our work db »] Les déclinaisons d'un tableau de bord (clé, libellé, jeton) sont enregistrées en base. Le jeton est généré par l'outil, jamais choisi à la main, et reste le même d'un rafraîchissement à l'autre : un lien partagé continue de fonctionner après le passage du cron et après une republication. Révision 2026-10-02 — par défaut, le jeton d'une déclinaison est sa clé (`?q=78`, `data/78.json`) ; il est un UUID généré par l'outil seulement quand le tableau le demande (`update_dashboard --obfuscate-variants`), et alors pour toutes ses déclinaisons. Changer ce mode sur un tableau qui a déjà des déclinaisons est refusé : les liens partagés casseraient. Le jeton reste stable dans les deux modes. Motif : un nom de fichier lisible suffit tant que le lien n'a pas à être secret. Revalidé le 2026-10-02. Révision 2026-10-07 — quiconque peut modifier le tableau peut activer ou désactiver l'obfuscation à tout moment, déclinaisons déjà déclarées comprises (`update_dashboard --obfuscate-variants true|false`). Chaque déclinaison reçoit alors le jeton du nouveau mode, et son fichier de données le suit, en interne comme dans chaque snapshot publié : aucun contenu n'est perdu et aucun cron n'est à relancer. Les liens partagés de l'ancien mode cessent de fonctionner, ce que la commande signale. Si une copie échoue, aucun jeton ne change. Motif : refuser obligeait à retirer puis redéclarer chaque déclinaison. Revalidé le 2026-10-07.
**Commande** — `uv run --frozen pytest tests/test_variants_lib.py tests/test_dashboard_skill_scripts.py -k dod_4 -q`
**Code de sortie** — 0
**Sortie** — 

```
.............                                                            [100%]
13 passed, 32 deselected in 1.07s
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
