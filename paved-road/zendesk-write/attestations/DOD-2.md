# DOD-2

**Critère** — [du brief : « regarde cette URL, ajoute ça »] Quand je donne l'adresse d'un article et une retouche à y faire, Autometa me montre la modification exacte sur cet article seul, sans toucher aux autres.
**Commande** — `uv run --frozen pytest tests/test_zendesk_changeset.py -k dod_2_`
**Code de sortie** — 0
**Sortie** — 

```
============================= test session starts ==============================
platform darwin -- Python 3.14.6, pytest-9.0.3, pluggy-1.6.0
rootdir: /Users/louije/Development/gip/Autometa
configfile: pytest.ini
plugins: mock-3.15.1, cov-7.1.0, playwright-0.9.0, base-url-2.1.0, anyio-4.13.0
collected 41 items / 40 deselected / 1 selected

tests/test_zendesk_changeset.py .                                        [100%]

======================= 1 passed, 40 deselected in 0.38s =======================
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
