# DOD-12

**Critère** — [du brief : « rendu headless »] Quand la page n'a pas fini de charger au bout de 30 secondes, le verdict est « échoué » avec le problème « délai dépassé », et l'agent obtient un verdict au lieu d'attendre indéfiniment.
**Commande** — `uv run --frozen pytest tests/test_dashboard_quality.py browser/test_verify_dashboard.py -k dod_12_`
**Code de sortie** — 0
**Sortie** — 

```
============================= test session starts ==============================
platform linux -- Python 3.14.3, pytest-9.0.3, pluggy-1.6.0
rootdir: /home/alexisakinyemi/autometa-pymc-clawdio-0986b736
configfile: pytest.ini
plugins: anyio-4.13.0, mock-3.15.1, base-url-2.1.0, cov-7.1.0, playwright-0.9.0
collected 41 items / 39 deselected / 2 selected

tests/test_dashboard_quality.py ..                                       [100%]

======================= 2 passed, 39 deselected in 2.22s =======================
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
