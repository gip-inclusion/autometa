---
name: update_dashboard
description: Update a dashboard's metadata (title, description, tags, flags, archive). MUST be invoked whenever the user wants to modify an existing dashboard — guarantees the right slug is targeted and reloads coding conventions.
---

# Update Dashboard Skill

**Point d'entrée canonique** pour toute modification d'un tableau de bord existant. Dès qu'un utilisateur exprime le souhait de modifier un TDB, lance ce skill **avant** de toucher aux fichiers du dossier. Il :

- Résout le slug (échec explicite si inconnu).
- Met à jour les métadonnées DB en transaction.
- Synchronise le frontmatter `APP.md` du workspace si les champs concernés changent.
- Renvoie l'`originating_user_email` (premier auteur, ≠ utilisateur courant) et les conventions de codage à respecter pour la suite.

## Avant de lancer

**Toujours confirmer la cible avec l'utilisateur si le slug n'a pas été donné explicitement** (par URL ou nom exact). L'erreur classique est de modifier le mauvais TDB ou de recréer un doublon en croyant éditer.

1. Lister les candidats actifs :
   ```bash
   .venv/bin/python skills/list_dashboards.py | grep -i <indice>
   ```
2. **Aucun match** : c'est probablement une création — pivoter vers `create_dashboard`, ou demander à l'utilisateur de clarifier.
3. **Un seul match** : présenter le titre et le lien `/interactive/{slug}/` à l'utilisateur, et demander confirmation explicite avant d'invoquer `update_dashboard`.
4. **Plusieurs matches** : les lister (titre + lien) et laisser l'utilisateur trancher.

Ne jamais inventer ou deviner un slug.

## Usage

```bash
.venv/bin/python skills/update_dashboard/scripts/update_dashboard.py \
    --slug mon-tdb \
    --title "Nouveau titre" \
    --add-tags trafic,emplois \
    --remove-tags ancien-tag \
    --has-api-access true
```

Sortie sur stdout (JSON) :

```json
{
  "slug": "mon-tdb",
  "originating_user_email": "alice@inclusion.gouv.fr",
  "updater_email": "bob@inclusion.gouv.fr",
  "fields_changed": ["title", "has_api_access", "tags"],
  "directory": "data/interactive/mon-tdb",
  "conventions_doc_path": "docs/interactive-dashboards.md"
}
```

L'agent **DOIT** lire `conventions_doc_path` (avec son outil Read) avant de modifier les fichiers du TDB.

## CLI Options

| Option | Description |
|--------|-------------|
| `--slug` | (obligatoire) Slug du TDB à modifier |
| `--title` | Nouveau titre |
| `--description` | Nouvelle description (une ligne) |
| `--website` | Nouveau site associé |
| `--category` | Nouvelle catégorie |
| `--add-tags TAG1,TAG2` | Tags à ajouter |
| `--remove-tags TAG1,TAG2` | Tags à retirer |
| `--set-tags TAG1,TAG2` | Remplace tout l'ensemble (mutuellement exclusif avec `--add-tags`/`--remove-tags`) |
| `--has-cron true\|false` | Met à jour le flag |
| `--has-api-access true\|false` | Met à jour le flag |
| `--has-persistence true\|false` | Met à jour le flag |
| `--archive` | Passe `is_archived=true` |
| `--unarchive` | Passe `is_archived=false` |

> **Note** : `--has-cron`, `--has-api-access`, `--has-persistence` attendent une valeur explicite `true|false` (contrairement à `create_dashboard` où ce sont des flags sans valeur). C'est volontaire — ici il faut pouvoir *désactiver* un flag déjà à `true`, alors qu'à la création le défaut est toujours `false`.

Sans aucun argument modificateur, le skill ne touche pas la DB et retourne juste les conventions.

## Variables d'environnement

Injectées automatiquement par `web/agents/cli.py` :

- `AUTOMETA_CONVERSATION_ID` — id de la conversation courante (loggée pour audit).
- `AUTOMETA_USER_EMAIL` — email de l'utilisateur qui modifie (`updater_email` dans le retour).

L'`originating_user_email` (= premier auteur du TDB) est lu en DB par la fonction `lib/`.

## Codes de retour

- `0` — succès, JSON sur stdout.
- `1` — slug inconnu, mutex `--set-tags` ⇄ `--add-tags`/`--remove-tags`, ou autre erreur métier.
- `2` — variables d'env manquantes (bug d'intégration).
