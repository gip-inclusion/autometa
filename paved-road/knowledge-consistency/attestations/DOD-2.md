# DOD-2

**Critère** — [du brief : « un moyen plus générique »] Le numéro, le nom et l'adresse de chaque site suivi dans Matomo n'ont qu'une seule référence : le tableau des sites des consignes d'Autometa. Quand une fiche, un skill ou la configuration donnent pour un site un numéro, un nom ou un conteneur différent, ou citent une instance Metabase qui n'existe pas, la vérification de la PR échoue et nomme les deux valeurs.
**Commande** — `uv run --frozen pytest tests/test_knowledge_consistency.py -k dod_2`
**Code de sortie** — 0
**Sortie** — 

```
============================= test session starts ==============================
platform linux -- Python 3.14.3, pytest-9.0.3, pluggy-1.6.0
rootdir: /home/alexisakinyemi/autometa-clawdio-a182a175
configfile: pytest.ini
plugins: anyio-4.13.0, mock-3.15.1, base-url-2.1.0, cov-7.1.0, playwright-0.9.0
collected 42 items / 33 deselected / 9 selected

tests/test_knowledge_consistency.py .........                            [100%]

======================= 9 passed, 33 deselected in 0.21s =======================
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
