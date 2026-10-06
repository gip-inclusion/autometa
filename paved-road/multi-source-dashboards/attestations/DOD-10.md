# DOD-10

**Critère** — [condition de sûreté du lien] La copie publiée d'un tableau multi-sources ne contient aucun fichier qui énumère les déclinaisons ou leurs jetons, et le tableau ne transmet pas le jeton aux sites externes qu'il lie (pas de referrer sortant).
**Commande** — `uv run --frozen pytest tests/test_multi_source_template.py -k dod_10 -q`
**Code de sortie** — 0
**Sortie** — 

```
.                                                                        [100%]
1 passed, 5 deselected in 0.62s
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `198be3e0ca19c7344346b460f47632a7997c1a8b` |
| `lib` | `84a1e7d287295a59e01cb7c7538590bc2859cd10` |
| `scripts` | `1db5541ee291f83cc7f58352cd6e10d88881ebf6` |
| `skills` | `7b027d42d1f92f23e8e4d4564a145642ca751e07` |
| `alembic` | `4199ab20c8200527287a4d1328e495721ee59ab2` |
| `tests` | `ec3304b8db8c97656f9df8252c87a26ab455a11c` |
| `browser` | `3838fcc50ff5c25b4f975d5d2bdbc060a2ca9cca` |

**Verdict** — démontré.
