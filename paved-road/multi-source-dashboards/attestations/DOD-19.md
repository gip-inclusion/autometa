# DOD-19

**Critère** — [lentille gap-hunter : fuite du jeton ; précision du demandeur] Matomo suit chaque déclinaison sous une URL lisible, `/interactive/{slug}/{clé}/`, transmise au traceur à la place de l'URL réelle : la clé et le libellé sont écrits par le cron dans le fichier de données, le jeton n'y figure jamais. Le jeton ne sort pas de l'URL : ni dans l'URL suivie par Matomo, ni dans le titre de l'onglet, ni dans le nom des fichiers exportés.
**Commande** — `uv run --frozen pytest browser/test_variants_page.py -k dod_19 -q`
**Code de sortie** — 0
**Sortie** — 

```
.                                                                        [100%]
1 passed, 9 deselected in 0.87s
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
