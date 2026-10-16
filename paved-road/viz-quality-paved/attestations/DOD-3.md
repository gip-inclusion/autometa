# DOD-3

**Critère** — [du brief : « requêtes de ressources en échec »] Quand un fichier dont le tableau de bord a besoin pour fonctionner (ses données, un script, une feuille de style) ne se charge pas, le verdict est « échoué » et le problème nomme ce fichier.
**Commande** — `uv run --frozen pytest tests/test_dashboard_quality.py browser/test_verify_dashboard.py -k dod_3_`
**Code de sortie** — 0
**Sortie** — 

```
============================= test session starts ==============================
platform linux -- Python 3.14.3, pytest-9.0.3, pluggy-1.6.0
rootdir: /home/alexisakinyemi/autometa-pymc-clawdio-0986b736
configfile: pytest.ini
plugins: anyio-4.13.0, mock-3.15.1, base-url-2.1.0, cov-7.1.0, playwright-0.9.0
collected 41 items / 37 deselected / 4 selected

tests/test_dashboard_quality.py ...                                      [ 75%]
browser/test_verify_dashboard.py .                                       [100%]

======================= 4 passed, 37 deselected in 3.56s =======================
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `0c808ef40dcc7fe9a60a1834854a2c3a9fcc636c` |
| `lib` | `dfdc2864780e1bc9795d8888f3a2a0144e4fbf85` |
| `scripts` | `a39688dfae8442c2bd6c098d0d94cf53a4825f78` |
| `skills` | `c63680150e7f3a9e895838c927e1c0f6fe4d9ab4` |
| `alembic` | `f16ee5bae3fe5b0639825bd366dde9877bb77884` |
| `tests` | `fe1c0d10187fcbd339d040ee10b8d553b711d247` |
| `browser` | `29732ca57a2371091cd065af0ef4fdc10384f8c7` |

**Verdict** — démontré.
