# DOD-2

**Critère** — Le fichier téléchargé porte le titre du rapport dans son nom, et l'extension `.md`. Cas couverts : « Bilan mensuel des candidatures », « Rapport « été 2026 » — pass IAE ».

**Commande** — `uv run --frozen pytest tests/test_rapports.py -k "test_rapport_markdown_filename" -q`

**Code de sortie** — 0

**Sortie** — `4 passed, 14 deselected, 1 warning in 1.53s`

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `aaa008c06fa8b56ac7d2a770e599491cba675106` |
| `tests` | `1cb798b830399cb822a266575e0bc4a75b57c637` |

**Verdict** — démontré.
