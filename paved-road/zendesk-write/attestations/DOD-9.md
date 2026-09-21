# DOD-9

**Critère** — [du brief : « regarde cette URL »] Quand une proposition ne changerait rien (le mot cherché n'apparaît nulle part, la retouche laisse l'article identique), Autometa me le dit et aucune proposition n'est créée.
**Commande** — `uv run --frozen pytest tests/test_zendesk_changeset.py -k dod_9_`
**Code de sortie** — 0
**Sortie** — 

```
============================= test session starts ==============================
platform darwin -- Python 3.14.6, pytest-9.0.3, pluggy-1.6.0
rootdir: /Users/louije/Development/gip/Autometa
configfile: pytest.ini
plugins: mock-3.15.1, cov-7.1.0, playwright-0.9.0, base-url-2.1.0, anyio-4.13.0
collected 41 items / 39 deselected / 2 selected

tests/test_zendesk_changeset.py ..                                       [100%]

======================= 2 passed, 39 deselected in 0.24s =======================
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `8eb2cf007275989e4a2a4bfe7c94dbfaa0bb8dba` |
| `lib` | `d45b63aab61ba3d3a105194be3f9b36b88839e1e` |
| `scripts` | `a4d9138781a04d96661f9e8647f4867cf513d756` |
| `skills` | `7c128e350e1ce205275fe35019db54ad2e264e52` |
| `alembic` | `78d86fc32fd67e7792b9050474ff4a65a14753d5` |
| `tests` | `f837990eb25439dc209d8b09d6e651e6f4d4fdb2` |
| `browser` | `a74249cb83790092cc89b32a05588fe41bf6fc70` |

**Verdict** — démontré.
