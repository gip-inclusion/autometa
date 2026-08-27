# DOD-4

**Critère** — Quand le titre du rapport ne donne aucun nom de fichier lisible, alors le fichier s'appelle `rapport-<numéro du rapport>.md`. Cas couverts : titre vide, titre réduit à des caractères spéciaux.

**Commande** — `uv run --frozen pytest tests/test_rapports.py -k "test_rapport_markdown_filename" -q`

**Code de sortie** — 0

**Sortie** — `4 passed, 14 deselected, 1 warning in 1.53s`

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `aaa008c06fa8b56ac7d2a770e599491cba675106` |
| `tests` | `1cb798b830399cb822a266575e0bc4a75b57c637` |

**Verdict** — démontré.
