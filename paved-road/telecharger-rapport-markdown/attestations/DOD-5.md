# DOD-5

**Critère** — Les liens déjà partagés vers la « version exportable » d'un rapport continuent de mener à ce rapport.

**Commande** — `uv run --frozen pytest tests/test_rapports.py -k "test_rapport_txt_redirects_to_markdown" -q`

**Code de sortie** — 0

**Sortie** — `1 passed, 17 deselected, 1 warning in 1.29s`

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `aaa008c06fa8b56ac7d2a770e599491cba675106` |
| `tests` | `1cb798b830399cb822a266575e0bc4a75b57c637` |

**Verdict** — démontré.
