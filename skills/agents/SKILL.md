---
name: agents
description: Créer un agent (un job qui traite des données et écrit dans Slack ou Notion, avec au besoin un classificateur et des préparations par crons), seulement après confirmation explicite de l'utilisateur dans un message suivant ; retirer un agent ; livrer la sortie d'un de ses runs ; faire relire et approuver ses productions. À utiliser dès que l'utilisateur veut un job récurrent qui dépose ses résultats dans un canal Slack ou une base Notion.
---

# Agents

Un agent est un job du moteur de jobs (page `/jobs`, nommé `agent-<slug>`) accompagné d'une
configuration au format `pdi.agent/1`. Le worker du job n'écrit nulle part : il rend un JSON
d'envois, et c'est Autometa qui les livre, seulement vers les destinations de la liste fermée
`config/agent_destinations.yaml`, selon le mode choisi pour chacune :

- `ombre` : l'envoi est enregistré, rien n'est écrit. Mode par défaut d'un nouvel agent.
- `relecture` : rien n'est écrit tant qu'une personne n'a pas approuvé l'envoi.
- `reel` : écrit directement ; refusé tant que l'agent n'est pas dans `reel_autorise` de la
  destination, ce qui s'ouvre par une PR, jamais depuis une conversation.

## Commencer par la liste

```bash
.venv/bin/python skills/agents/scripts/agents.py destinations
```

Elle rend tout ce qu'un agent peut utiliser : destinations (et si leur cible est configurée sur
cette instance), modèles, préparations, cadences. Ne jamais chercher ces listes dans le dépôt ni
dans l'environnement. Une destination sans cible reste proposable : ses envois en mode `reel`
seront en échec tant que la cible manque, ce qu'il faut dire à l'utilisateur.

## Configuration

```yaml
format: pdi.agent/1
slug: signaux-faibles-mep            # devient le job agent-signaux-faibles-mep
titre: Signaux faibles des mises en production
mission: >-                           # 20 à 400 caractères, ni lien, ni @personne, ni #canal
  Signaler à l'équipe produit les MEP dont l'effet n'est pas mesurable.
points_de_contact:                    # 1 à 6 destinations de config/agent_destinations.yaml
  - id: produit.signal_faible
    mode: ombre
cadence: quotidienne                  # facultatif : quotidienne, hebdomadaire, mensuelle ; absent = à la demande
outils_modeles:                       # facultatif, 3 au plus, modèles de config/agent_modeles.yaml
  - id: classifieur.pertinence
    question: La production signale-t-elle une MEP dont l'effet n'est pas mesurable ?
    seuil: 0.7                        # sous ce seuil, la production n'est pas livrée (gardée, statut ecarte)
preparations:                         # facultatif, 3 au plus, dans l'ordre ; ce qui nourrit chaque run
  - type: cron                        # la dernière sortie réussie d'une tâche de cron/ (jamais relancée)
    tache: sync-tags
  - type: notion                      # les lignes d'une base Notion partagée avec l'intégration
    base: 0123456789abcdef0123456789abcdef
  - type: s3                          # un jeu publié par publish_dataset (URL transmise au run)
    jeu: services.sqlite
```

Aucun autre champ n'est accepté. Ne jamais inventer une destination : lire la liste. Si aucune
ne convient, le dire à l'utilisateur ; une destination nouvelle s'ajoute par une PR.

La consigne du job se compose comme pour `compose_and_launch_job` (étapes 1 à 4 : le worker n'a
aucun accès aux données ni au contexte d'Autometa). Le contrat de sortie JSON y est ajouté
automatiquement, avec la liste des destinations de l'agent.

## Agents déclarés dans le dépôt

Un agent peut aussi arriver par une PR : sa configuration `agents/<slug>.yaml` et sa consigne
`agents/<slug>.md`, relues en PR et validées par la CI. Il s'enregistre par le même déroulé, avec
ces deux fichiers tels quels : `proposer --config agents/<slug>.yaml --consigne agents/<slug>.md`,
puis `creer` au tour suivant. Ne pas réécrire la consigne d'un agent du dépôt : une correction
passe par une PR.

## Déroulé imposé

```bash
S=skills/agents/scripts/agents.py
.venv/bin/python $S proposer --config /tmp/agent.yaml --consigne /tmp/consigne.md
.venv/bin/python $S creer <proposition>       # tour suivant, après le oui de l'utilisateur
.venv/bin/python $S retirer <proposition>
.venv/bin/python $S voir <proposition>
```

1. Rédiger la configuration et la consigne, appeler `proposer`. Rien n'est créé. Une
   configuration refusée rend des messages qui nomment le champ et la correction : corriger et
   reproposer.
2. Terminer le tour par la relecture : titre, mission, chaque destination avec son mode, le
   classificateur (question, seuil), les préparations dans l'ordre, la cadence, un aperçu de la
   consigne, l'identifiant de la proposition, et la question « Je crée cet agent ? ».
3. **Ne jamais appeler `creer` dans le tour de `proposer`.** Le code le refuse de toute façon :
   la création exige un message de l'utilisateur postérieur à la proposition, dans la même
   conversation. Si la réponse est ambiguë, ne pas créer. Une correction demandée donne une
   nouvelle proposition ; l'ancienne reste sans effet.
4. Après `creer`, donner le lien du job (`/jobs`) et rappeler que `retirer` arrête toute
   livraison. Lancer un run reste soumis à la confirmation de `compose_and_launch_job`.

## Faire tourner un agent

Un agent n'est pas un processus allumé : chaque run est un conteneur jetable qui va au bout puis
disparaît. Aucun agent n'a de cron à lui : avec une `cadence`, le seul cron des agents,
`run-agents`, enchaîne chaque matin préparations, run, classificateur et livraison.

| Action | Garde |
|---|---|
| lire (configuration, runs, envois) | aucune |
| lancer un run maintenant | `proposer-lancement`, puis `lancer` au tour suivant, après le oui |
| modifier la configuration, la consigne ou la cadence | `proposer` avec le même slug (une modification), `creer` après le oui, `retirer` pour revenir en arrière |
| passer une destination en réel | jamais depuis la conversation : une PR sur `reel_autorise` |

```bash
.venv/bin/python $S proposer-lancement --agent <slug>   # montre les préparations, ne lance rien
.venv/bin/python $S lancer --agent <slug>               # tour suivant, après le oui de l'utilisateur
```

Le code refuse un `lancer` sans message ultérieur de l'utilisateur, et une confirmation ne sert
qu'une fois. Une préparation sans contenu (cron sans dernière sortie réussie, jeu S3 absent)
empêche le run.

## Livrer un run et relire ses productions

```bash
.venv/bin/python $S livrer --agent <slug> --run <run_id>
.venv/bin/python $S montrer-envoi --agent <slug> --envoi <id>
.venv/bin/python $S approuver-envoi --agent <slug> --envoi <id>   # tour suivant, après le oui
```

`livrer` n'accepte qu'un run terminé du job de l'agent ; relivrer le même run n'écrit rien de
plus. Une seule destination hors liste fait refuser tout le run. Rendre compte de chaque envoi
(destination, mode, statut : `ombre`, `a_relire`, `envoyee`, `echec`, `ecarte` quand le
classificateur l'a jugée sous le seuil). Pour un envoi `a_relire`,
`montrer-envoi` puis afficher son titre et son texte, demander la validation, et n'appeler
`approuver-envoi` qu'au tour suivant. Un envoi `echec` se réessaie de la même façon.
