---
name: create_dashboard
description: Create a new dashboard (TDB) — scaffolds files and inserts a row in the dashboards table. Use this skill instead of writing files directly.
---

# Create Dashboard Skill

Crée un nouveau tableau de bord (TDB) : copie le template dans `data/interactive/{slug}/`, génère `APP.md` à partir des arguments, insère la ligne `dashboards` + tags. Chemin **unique** de création côté agent — ne jamais écrire les fichiers à la main.

## Avant de créer

**Vérifier qu'aucun TDB proche n'existe déjà.** L'erreur classique est de créer un doublon en croyant qu'il s'agit d'un nouveau TDB alors que l'utilisateur veut modifier l'existant.

1. Lister les candidats actifs sur le thème :
   ```bash
   python skills/list_dashboards.py | grep -i <thème ou mots-clés>
   ```
2. **Aucun match** : c'est bien une création — continuer.
3. **Match proche** (par titre, slug ou sujet) : présenter le candidat à l'utilisateur (titre + lien `/interactive/{slug}/`) et lui demander s'il préfère modifier l'existant via `update_dashboard` plutôt que créer un nouveau TDB.
4. **Slug envisagé déjà pris** : le skill échouera avec `Slug already exists`. Pivoter vers `update_dashboard` après confirmation.

## Usage
```bash
.venv/bin/python skills/create_dashboard/scripts/create_dashboard.py \
    --slug mon-tdb \
    --title "Mon tableau de bord" \
    --description "Description courte (une ligne)" \
    --website emplois \
    --category "Analyse de trafic" \
    --tags trafic,candidats \
    --has-cron
```

Sortie sur stdout (JSON) :

```json
{
  "slug": "mon-tdb",
  "directory": "data/interactive/mon-tdb",
  "first_author_email": "alice@inclusion.gouv.fr",
  "conversation_id": "uuid-of-creating-conversation",
  "created_at": "2026-05-08T14:32:11+00:00"
}
```

## CLI Options

| Option | Required | Description |
|--------|----------|-------------|
| `--slug` | yes | Slug du TDB (lowercase, kebab-case, regex `^[a-z0-9]+(-[a-z0-9]+)*$`) |
| `--title` | yes | Titre lisible |
| `--description` | yes | Description courte (une ligne, va dans le frontmatter) |
| `--website` | | Site associé (`emplois`, `dora`, `marche`, etc.) |
| `--category` | | Catégorie libre |
| `--tags` | | Tags CSV (`trafic,candidats,analyse`) |
| `--has-cron` | | Inclure `cron.py` du template + flag DB à `true` |
| `--has-api-access` | | Flag DB à `true` (TDB qui appelle `/api/query` en live, **non publiable**) |
| `--has-persistence` | | Flag DB à `true` (TDB qui écrit dans le datalake, **non publiable**) |

## Variables d'environnement

Injectées automatiquement par `web/agents/cli.py` au démarrage du sous-process agent :

- `AUTOMETA_CONVERSATION_ID` — id de la conversation courante (persisté dans `dashboards.created_in_conversation_id`).
- `AUTOMETA_USER_EMAIL` — email de l'utilisateur qui crée (persisté dans `dashboards.first_author_email`).

Si l'une manque, le script échoue avec code retour non nul.

## Conventions de codage

Avant d'écrire le code du TDB (HTML/JS/cron.py), lire `docs/interactive-dashboards.md` pour respecter les conventions (vanilla JS, pas de framework, palette DSFR, structure des fichiers, modes `cron.py` vs `/api/query`).
