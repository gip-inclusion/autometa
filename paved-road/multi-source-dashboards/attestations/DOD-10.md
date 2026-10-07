# DOD-10

**Critère** — [condition de sûreté du lien] La copie publiée d'un tableau multi-sources ne contient aucun fichier qui énumère les déclinaisons ou leurs jetons, et le tableau ne transmet pas le jeton aux sites externes qu'il lie (pas de referrer sortant).
**Commande** — `uv run --frozen pytest tests/test_multi_source_template.py -k dod_10 -q`
**Code de sortie** — 0
**Sortie** — 

```
.                                                                        [100%]
1 passed, 5 deselected in 0.36s
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `025f36cf58659e483324d1a6cfc73a6df9549b0a` |
| `lib` | `857b7b5f0d013efe0b7a0a185fffe090db79d3a7` |
| `scripts` | `1db5541ee291f83cc7f58352cd6e10d88881ebf6` |
| `skills` | `4cd9e2f4ac9726e2a7cfd34ece88e82aaea1f745` |
| `alembic` | `4199ab20c8200527287a4d1328e495721ee59ab2` |
| `tests` | `5e5459c774ff6e8e55e094e1d678b509109e3517` |
| `browser` | `3838fcc50ff5c25b4f975d5d2bdbc060a2ca9cca` |

**Verdict** — démontré.
