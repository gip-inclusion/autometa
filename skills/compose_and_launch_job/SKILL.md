---
name: compose_and_launch_job
description: Composer un system prompt riche en contexte métier et lancer un run autometa-jobs à partir de l'intention de l'utilisateur. À utiliser quand l'utilisateur veut une analyse autonome et longue (minutes à heures), trop lourde ou trop lente pour le chat interactif — par ex. « lance un job qui analyse tous les services Dora ».
---

# Composer & lancer un job

C'est vous qui composez le system prompt du job ; **l'utilisateur ne l'écrit jamais**. Un worker autometa-jobs est un conteneur Claude vierge sur Scaleway : il n'a **aucun accès PG, pas de `knowledge/`, pas de `CLAUDE.md`, aucun contexte métier d'Autometa**, et il ne peut rien lire de tout cela à l'exécution. C'est donc à vous — qui détenez la connaissance métier — de distiller le contexte pertinent et de tout embarquer (contexte, données, tâche) dans un **prompt autosuffisant**.

## Quand l'utiliser

L'utilisateur demande un travail autonome et long (trop lourd/lent pour le runner interactif) : « analyse tous les services Dora et rédige un rapport », « passe en revue toutes les SIAE de la région X », un brief hebdomadaire. Pour une question rapide, répondez directement dans le chat — ne lancez pas de job.

## Recette

1. **Clarifier** la tâche et le livrable attendu (un rapport ? un tableau ? une reco ?). Ne demandez que ce que vous ne pouvez pas déduire.

2. **Rassembler la connaissance métier pertinente.** Lisez les fichiers `knowledge/` utiles (par ex. `knowledge/sites/dora.md`, le contexte IAE, le schéma des données). **Sélectionnez, ne déversez pas** — le worker n'a rien.

3. **Préparer les données** (si le job analyse un jeu de données). Utilisez la skill **`publish_dataset`** pour exporter le(s) résultat(s) de requête vers S3 et obtenir une URL présignée + le schéma. Pour des données relationnelles, utilisez le mode multi-tables (`--tables`) afin que le worker puisse faire des JOIN.

4. **Composer un system prompt autosuffisant.** Il doit porter tout ce qui manque au worker :
   - **Rôle + contexte métier** — le contexte IAE / site / Dora distillé, pertinent pour la tâche (ce que signifient les entités et les colonnes, comment les interpréter).
   - **Accès aux données** — par ex. `Télécharge le jeu de données : curl -sL '<url-présignée>' -o data.sqlite`. Précisez le format, les noms de tables, les colonnes.
   - **La tâche** — étapes concrètes et question à résoudre.
   - **Le livrable** — ce que doit être l'artefact final (le dernier message du worker devient l'artefact).
   - **Note d'environnement** — le sandbox dispose de `Bash`, `python3` (stdlib `sqlite3`, plus `numpy`/`pandas`), `curl`, `git` ; aucune API Autometa.

   Écrivez le prompt dans un fichier (évite les soucis d'échappement shell).

5. **⚠️ Faire valider le lancement — étape obligatoire.** Un job consomme du quota Claude et un conteneur Scaleway facturé, tourne en autonomie jusqu'à 24 h, et la concurrence est de 1 (un nouveau run patiente derrière un run en cours). **Avant de lancer**, présentez un récapitulatif à l'utilisateur :
   - la tâche et le livrable,
   - les données embarquées (jeu, nombre de lignes),
   - les paramètres (`max_turns`, outils autorisés),
   - un aperçu du system prompt composé.

   Puis **demandez une confirmation explicite** (« Je lance ce job ? »). **N'exécutez `launch_job.py` que si l'utilisateur confirme explicitement.** En cas de doute ou de réponse ambiguë, ne lancez pas.

6. **Lancer** (uniquement après confirmation) :

   ```bash
   .venv/bin/python skills/compose_and_launch_job/scripts/launch_job.py \
       --name dora-services-2026-06 \
       --system-prompt-file /tmp/job_prompt.md \
       --max-turns 40 \
       --allowed-tools "Bash,Read,WebFetch"
   ```

   Affiche `{ "pipeline_id", "run_id", "status", "run_url" }`. Le `--name` doit être **unique** (incluez une date/un slug) ; en cas de collision l'orchestrateur renvoie une erreur — réessayez avec un autre nom.

7. **Rendre le `run_url`** à l'utilisateur pour qu'il suive le run sur `/jobs/runs/{run_id}` (statut, flux d'événements en direct, résumé, artefact). Précisez qu'il tourne en autonomie ; pas besoin de rester.

## Limites

- Un job coûte du quota et un conteneur Scaleway (concurrence 1). Ne lancez pas de job pour un travail trivial.
- Gardez le prompt autosuffisant et la connaissance ciblée — le superflu coûte des tokens et de l'argent. Si le contexte est volumineux, embarquez-le comme `context.md` à côté des données (via `publish_dataset`) et demandez au worker de le lire d'abord.
