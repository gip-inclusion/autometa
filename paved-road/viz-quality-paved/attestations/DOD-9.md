# DOD-9

**Critère** — [du brief : « requêtes de ressources en échec »] Quand le tableau de bord lit ses données en direct auprès d'Autometa, ces lectures, impossibles hors de l'application, ne font pas échouer le verdict : elles sortent en avertissement « données en direct non vérifiées ». Révision 2026-09-18 — la lentille `design-coherence` a montré qu'hors de l'application, une page privée de ses données en direct échoue presque toujours par ricochet (erreur JavaScript, graphique vide, bloc d'erreur) : « ne font pas échouer le verdict » ne tient que pour la lecture elle-même. Le critère devient : la lecture en direct sort en avertissement « données en direct non vérifiées », les problèmes qu'elle entraîne restent signalés, et les consignes disent à l'agent de ne pas s'y acharner — il donne le lien en précisant que la vérification n'a pas pu voir les données en direct. Revalidé le 2026-09-18, par délégation.
**Commande** — `uv run --frozen pytest tests/test_dashboard_quality.py browser/test_verify_dashboard.py -k dod_9_`
**Code de sortie** — 0
**Sortie** — 

```
============================= test session starts ==============================
platform linux -- Python 3.14.3, pytest-9.0.3, pluggy-1.6.0
rootdir: /home/alexisakinyemi/autometa-pymc-clawdio-0986b736
configfile: pytest.ini
plugins: anyio-4.13.0, mock-3.15.1, base-url-2.1.0, cov-7.1.0, playwright-0.9.0
collected 41 items / 40 deselected / 1 selected

tests/test_dashboard_quality.py .                                        [100%]

======================= 1 passed, 40 deselected in 2.22s =======================
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
