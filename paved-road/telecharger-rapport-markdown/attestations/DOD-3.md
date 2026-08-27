# DOD-3

**Critère** — Le fichier contient le texte du rapport tel qu'il a été écrit, sans rien retirer ni ajouter.

**Commande** — `uv run --frozen pytest tests/test_rapports.py -k "test_rapport_markdown_keeps_the_report_text_untouched" -q`

**Code de sortie** — 0

**Sortie** — `1 passed, 17 deselected, 1 warning in 1.34s`

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `aaa008c06fa8b56ac7d2a770e599491cba675106` |
| `tests` | `1cb798b830399cb822a266575e0bc4a75b57c637` |

**Verdict** — démontré.
