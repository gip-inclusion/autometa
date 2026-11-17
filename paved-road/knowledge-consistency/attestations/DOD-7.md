# DOD-7

**Critère** — [du brief : « ne pas laisser les infos contradictoires créer des comportements aléatoires »] Quand Autometa rencontre malgré tout deux consignes qui divergent, il applique un ordre de priorité écrit dans ses consignes (catalogue réel des bases, puis skill de la source, puis fiche de connaissance) et le signale dans sa réponse au lieu de choisir en silence. Ce critère décrit un comportement du modèle : il ne se démontre pas par un test automatique. Sa preuve sera la présence de la règle, à un seul endroit, dans les consignes.
**Commande** — `uv run --frozen pytest tests/test_knowledge_consistency.py -k dod_7`
**Code de sortie** — 0
**Sortie** — 

```
============================= test session starts ==============================
platform linux -- Python 3.14.3, pytest-9.0.3, pluggy-1.6.0
rootdir: /home/alexisakinyemi/autometa-clawdio-a182a175
configfile: pytest.ini
plugins: anyio-4.13.0, mock-3.15.1, base-url-2.1.0, cov-7.1.0, playwright-0.9.0
collected 50 items / 49 deselected / 1 selected

tests/test_knowledge_consistency.py .                                    [100%]

======================= 1 passed, 49 deselected in 0.18s =======================
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
