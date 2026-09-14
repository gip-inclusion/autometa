# DOD-12

**Critère** — [lentille gap-hunter : entrée hors limites] La clé d'une déclinaison est faite de lettres minuscules, chiffres et tirets (1 à 64 caractères) et le libellé est obligatoire. Une clé vide, avec espaces ou caractères spéciaux, ou un libellé vide, est refusée en nommant le champ fautif, sans rien créer. Deux déclinaisons peuvent porter le même libellé : la clé reste l'identifiant, et elle s'affiche à côté du libellé sur la page d'édition et sur l'index interne.
**Commande** — `uv run --frozen pytest tests/test_variants_lib.py -k dod_12 -q`
**Code de sortie** — 0
**Sortie** — 

```
........                                                                 [100%]
8 passed, 8 deselected in 0.70s
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `fc7ea2412f4440b60688cde4af450c28a87036cf` |
| `lib` | `dc9847fa9b2068ea45fa108a5b65181732339298` |
| `scripts` | `a4d9138781a04d96661f9e8647f4867cf513d756` |
| `skills` | `7909438b122995b1a074b7e22d91284e5dc06587` |
| `alembic` | `9dbb4fa33c1a7f59f3d1f956aa23798333baebf3` |
| `tests` | `673cde27ace5f05aba230ca875362a9c3a4ea86e` |
| `browser` | `e84a913b0c4e492f80b0c69655b3d975df4f39bb` |

**Verdict** — démontré.
