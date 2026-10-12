# DOD-3

**Critère** — [du brief : « ne pas laisser les infos contradictoires »] Chaque fiche de connaissance déclare la source de données qu'elle décrit et la date de sa dernière vérification. Une fiche qui ne le déclare pas, ou qui déclare une source inconnue, fait échouer la vérification. Une fiche vérifiée il y a plus de 180 jours est signalée, sans bloquer.
**Commande** — `uv run --frozen pytest tests/test_knowledge_consistency.py -k dod_3`
**Code de sortie** — 0
**Sortie** — 

```
…
_signalees_quand_elles_vieillissent
  /home/alexisakinyemi/autometa-clawdio-a182a175/tests/test_knowledge_consistency.py:170: UserWarning: fiche à revérifier : knowledge/stats/pass-iae.md:1 — vérifiée le 2026-01-05, il y a plus de 180 jours
    warnings.warn(f"fiche à revérifier : {finding}", stacklevel=1)

tests/test_knowledge_consistency.py::test_dod_3_les_fiches_du_depot_sont_signalees_quand_elles_vieillissent
  /home/alexisakinyemi/autometa-clawdio-a182a175/tests/test_knowledge_consistency.py:170: UserWarning: fiche à revérifier : knowledge/stats/prescribers.md:1 — vérifiée le 2026-01-05, il y a plus de 180 jours
    warnings.warn(f"fiche à revérifier : {finding}", stacklevel=1)

tests/test_knowledge_consistency.py::test_dod_3_les_fiches_du_depot_sont_signalees_quand_elles_vieillissent
  /home/alexisakinyemi/autometa-clawdio-a182a175/tests/test_knowledge_consistency.py:170: UserWarning: fiche à revérifier : knowledge/stats/structures.md:1 — vérifiée le 2026-01-13, il y a plus de 180 jours
    warnings.warn(f"fiche à revérifier : {finding}", stacklevel=1)

tests/test_knowledge_consistency.py::test_dod_3_les_fiches_du_depot_sont_signalees_quand_elles_vieillissent
  /home/alexisakinyemi/autometa-clawdio-a182a175/tests/test_knowledge_consistency.py:170: UserWarning: fiche à revérifier : knowledge/stats/support-emplois.md:1 — vérifiée le 2026-03-05, il y a plus de 180 jours
    warnings.warn(f"fiche à revérifier : {finding}", stacklevel=1)

tests/test_knowledge_consistency.py::test_dod_3_les_fiches_du_depot_sont_signalees_quand_elles_vieillissent
  /home/alexisakinyemi/autometa-clawdio-a182a175/tests/test_knowledge_consistency.py:170: UserWarning: fiche à revérifier : knowledge/webinaires/_index.md:1 — vérifiée le 2026-04-02, il y a plus de 180 jours
    warnings.warn(f"fiche à revérifier : {finding}", stacklevel=1)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
================ 5 passed, 37 deselected, 16 warnings in 0.21s =================
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `7423895be51dcdf75a277dd9c813ead8c4e2c3fc` |
| `lib` | `2bff3272ad1e3e0f797b1e76510b303dc35897b0` |
| `scripts` | `1db5541ee291f83cc7f58352cd6e10d88881ebf6` |
| `skills` | `d31ee1d21163d20f1ff65f7f058027772717c15d` |
| `alembic` | `4199ab20c8200527287a4d1328e495721ee59ab2` |
| `tests` | `1fce075c5d91dbd700f1b63d38a207fdfe1fc1cb` |
| `browser` | `3838fcc50ff5c25b4f975d5d2bdbc060a2ca9cca` |

**Verdict** — démontré.
