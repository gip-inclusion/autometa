# DOD-9

**Critère** — [du brief de phase 2 : « une doc knowledge/skill ne peut plus référencer une table/colonne inexistante », « valider contre un snapshot de catalogue committé »] Quand une fiche cite une table, ou une colonne d'une table, absente du catalogue des tables réelles de sa source (un instantané versionné dans le dépôt), la vérification échoue et nomme la fiche, la ligne et la table ou la colonne. Tant que l'instantané d'une source n'est pas versionné, la vérification le signale et ne contrôle pas les tables de cette source.
**Commande** — `uv run --frozen pytest tests/test_knowledge_consistency.py -k dod_9`
**Code de sortie** — 0
**Sortie** — 

```
…
ings.warn(str(finding), stacklevel=1)

tests/test_knowledge_consistency.py::test_dod_9_les_sources_du_depot_sans_instantane_sont_signalees
  /home/alexisakinyemi/autometa-clawdio-a182a175/tests/test_knowledge_consistency.py:334: UserWarning: knowledge/stats/prescribers.md:1 — tables non vérifiées : aucun instantané knowledge/catalog/metabase_stats.json
    warnings.warn(str(finding), stacklevel=1)

tests/test_knowledge_consistency.py::test_dod_9_les_sources_du_depot_sans_instantane_sont_signalees
  /home/alexisakinyemi/autometa-clawdio-a182a175/tests/test_knowledge_consistency.py:334: UserWarning: knowledge/stats/structures.md:1 — tables non vérifiées : aucun instantané knowledge/catalog/metabase_stats.json
    warnings.warn(str(finding), stacklevel=1)

tests/test_knowledge_consistency.py::test_dod_9_les_sources_du_depot_sans_instantane_sont_signalees
  /home/alexisakinyemi/autometa-clawdio-a182a175/tests/test_knowledge_consistency.py:334: UserWarning: knowledge/stats/support-emplois.md:1 — tables non vérifiées : aucun instantané knowledge/catalog/metabase_stats.json
    warnings.warn(str(finding), stacklevel=1)

tests/test_knowledge_consistency.py::test_dod_9_les_sources_du_depot_sans_instantane_sont_signalees
  /home/alexisakinyemi/autometa-clawdio-a182a175/tests/test_knowledge_consistency.py:334: UserWarning: knowledge/stats/users.md:1 — tables non vérifiées : aucun instantané knowledge/catalog/metabase_stats.json
    warnings.warn(str(finding), stacklevel=1)

tests/test_knowledge_consistency.py::test_dod_9_les_sources_du_depot_sans_instantane_sont_signalees
  /home/alexisakinyemi/autometa-clawdio-a182a175/tests/test_knowledge_consistency.py:334: UserWarning: knowledge/stats/users.md:1 — tables non vérifiées : aucun instantané knowledge/catalog/metabase_datalake.json
    warnings.warn(str(finding), stacklevel=1)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
================ 15 passed, 35 deselected, 19 warnings in 0.23s ================
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `7423895be51dcdf75a277dd9c813ead8c4e2c3fc` |
| `lib` | `e46e3f9f24bf5833d7ace923fa146be858c0ab1c` |
| `scripts` | `1db5541ee291f83cc7f58352cd6e10d88881ebf6` |
| `skills` | `d31ee1d21163d20f1ff65f7f058027772717c15d` |
| `alembic` | `4199ab20c8200527287a4d1328e495721ee59ab2` |
| `tests` | `e05959dfa1b68b4a5b508d499eda2c221bc48b13` |
| `browser` | `3838fcc50ff5c25b4f975d5d2bdbc060a2ca9cca` |

**Verdict** — démontré.
