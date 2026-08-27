# DOD-1

**Critère** — Quand je clique sur « Télécharger en Markdown » depuis un rapport, alors un fichier se télécharge, au lieu de s'afficher dans un onglet.

**Commande** — `uv run --frozen pytest tests/test_rapports.py -k "test_rapport_markdown_is_served_as_a_download or test_rapport_detail_view_has_download_button" -q`

**Code de sortie** — 0

**Sortie** — `2 passed, 16 deselected, 1 warning in 1.55s`

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `aaa008c06fa8b56ac7d2a770e599491cba675106` |
| `tests` | `1cb798b830399cb822a266575e0bc4a75b57c637` |

**Verdict** — démontré.
