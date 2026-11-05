---
name: agents
description: Créer un agent (un job récurrent ou à la demande qui lit des sources (bases et pages Notion, dépôts GitHub, pages web, jeux S3, sorties de crons), passe ses productions par des sous-agents Ollama (classificateur en filtre ou en étiquettes, extraction, résumé) et les dépose dans Slack, Notion ou ses propres fichiers versionnés), seulement après confirmation explicite de l'utilisateur dans un message suivant ; le modifier, le lancer, le retirer ; livrer ses runs, relire ses productions, lire et restaurer ses fichiers. À utiliser dès que l'utilisateur veut qu'un agent fasse un travail récurrent à partir de données.
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
python -m skills.agents.scripts.agents destinations
```

Elle rend tout ce qu'un agent peut utiliser : destinations (et si leur cible est configurée sur
cette instance), types de sous-agents et leurs modèles, types de préparation et leurs champs,
tâches de cron lisibles, cadences, limites des fichiers. Ne jamais chercher ces listes dans le
dépôt ni dans l'environnement.

## Composer un agent

Un agent s'assemble à partir de briques génériques ; aucune n'est propre à un cas. Avant de
répondre qu'une demande est impossible, la décomposer :

| L'utilisateur veut… | Brique |
|---|---|
| que l'agent lise une base ou une page Notion, un dépôt ou une organisation GitHub, une page web, un jeu S3, la sortie d'un cron | une `preparation` du type correspondant ; la source (identifiant, dépôt, URL) va dans la configuration |
| trier, ne garder que ce qui répond à une question | un `classificateur` en filtre (`question`, `seuil`) |
| ranger chaque production dans des catégories | un `classificateur` en étiquettes (`etiquettes`, `seuil`) : les catégories sont celles de l'utilisateur |
| des champs structurés, un texte court | une `extraction` (schéma), un `resume` (longueur) |
| un document que l'agent fait évoluer, ou une liste qu'on consulte en discutant | un `fichier` de l'agent, gardé dans Autometa et versionné |
| un rythme (tous les jours, deux fois par semaine, le lundi) | `cadence: {jours: [...]}` |
| écrire dans Slack ou Notion | un `point_de_contact` de la liste fermée |

Ce qui reste vraiment hors de portée : une source d'un type absent de la liste (un nouveau type
de préparation est un connecteur ajouté par une PR), une destination absente de la liste (une
PR), une heure de passage (le cron des agents tourne une fois par jour, le matin). Une destination sans cible reste proposable : ses envois en mode `reel`
seront en échec tant que la cible manque, ce qu'il faut dire à l'utilisateur.

## Configuration

```yaml
format: pdi.agent/1
slug: signaux-faibles-mep            # devient le job agent-signaux-faibles-mep
titre: Signaux faibles des mises en production
mission: >-                           # 20 à 400 caractères, ni lien, ni @personne, ni #canal
  Signaler à l'équipe produit les MEP dont l'effet n'est pas mesurable.
points_de_contact:                    # 0 à 6 destinations de la liste ; 0 seulement avec des fichiers
  - id: produit.signal_faible
    mode: ombre
cadence:                              # facultatif ; absent = à la demande
  jours: [lundi, jeudi]               # ou quotidienne, hebdomadaire (lundi), mensuelle (le 1er)
outils_modeles:                       # facultatif, 5 sous-agents au plus, appliqués dans cet ordre
  - type: classificateur              # filtre : une question oui/non ; sous le seuil, la production
    modele: "clef:27b"                # est gardée sans être livrée (ecarte) et la chaîne s'arrête
    question: La production signale-t-elle une MEP dont l'effet n'est pas mesurable ?
    seuil: 0.7
  - type: classificateur              # étiquettes : 1 à 10 catégories, une question chacune, en un
    modele: "clef:27b"                # seul appel ; chaque production reçoit celles qui passent le
    etiquettes:                       # seuil (ligne « Étiquettes : … »), rien n'est écarté
      - nom: urgent
        question: L'effet manquant touche-t-il des utilisateurs dès cette semaine ?
    seuil: 0.6
  - type: extraction                  # ajoute à la production les champs du schéma (1 à 10,
    modele: glm-5.2                   # types texte, nombre, entier, booleen)
    schema:
      application: texte
  - type: resume                      # réécrit la production en 100 à 3000 caractères
    modele: glm-5.2
    longueur_max: 600
preparations:                         # facultatif, 5 au plus, dans l'ordre ; chacune accepte plafond
  - type: notion                      # une base : filtre, colonnes, et au-delà du plafond un décompte
    base: 0123456789abcdef0123456789abcdef   # par regrouper_par suivi des lignes les plus récentes
    filtre:
      - {colonne: Statut, parmi: [À faire, En cours]}
      - {colonne: derniere_modification, apres: 2026-01-01}
    colonnes: [Nom, Statut]
    regrouper_par: [Statut]
    plafond: 60000
  - type: notion                      # une page et ses sous-pages, jusqu'à profondeur (1 à 3)
    page: fedcba9876543210fedcba9876543210
  - type: github                      # dépôts publics : depots d'abord, puis ceux de organisation ;
    depots: [proprietaire/depot]      # au-delà du plafond, le run suivant reprend où celui-ci s'arrête
    organisation: proprietaire
  - type: url                         # une page web ou un fichier texte public en https
    url: https://example.org/notes.md
  - type: cron                        # la dernière sortie réussie d'une tâche de cron/ (jamais relancée)
    tache: sync-tags                  # s3 : un jeu publié par publish_dataset (jeu: services.sqlite)
fichiers: [notes.md]                  # facultatif, 5 au plus, md, txt, csv ou json, 100 000 caractères
```

Les types de préparation et leurs champs exacts sont ceux que rend `destinations` ; une base ou
une page Notion doit être partagée avec l'intégration Notion d'Autometa (••• > Connexions), sinon
la préparation le dit et le run n'est pas lancé. GitHub n'est lu que pour les dépôts publics.

Les fichiers de l'agent restent dans Autometa : chacun est donné au run (dernière version) et
l'agent en rend une nouvelle version entière (`"fichiers"` dans sa sortie) ou y range des
productions une par une (`destination: fichier:<nom>`, après les sous-agents, étiquettes
comprises). Chaque écriture est une version ; écrire n'a pas besoin de confirmation, revenir à une
version ancienne si. Pour qu'un classificateur juge chaque élément, la consigne demande un envoi
par élément (un ticket, un signal), jamais une liste dans un seul envoi.

Les sous-agents sont appelés par Autometa après le run, avant la livraison, sur chaque
production ; le type et le modèle viennent de la liste rendue par `destinations`. Aucun autre
champ n'est accepté. Ne jamais inventer une destination : lire la liste. Si aucune
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
python -m skills.agents.scripts.agents proposer --config /tmp/agent.yaml --consigne /tmp/consigne.md
python -m skills.agents.scripts.agents creer <proposition>       # tour suivant, après le oui de l'utilisateur
python -m skills.agents.scripts.agents retirer <proposition>
python -m skills.agents.scripts.agents voir <proposition>
```

1. Rédiger la configuration et la consigne, appeler `proposer`. Rien n'est créé. Une
   configuration refusée rend des messages qui nomment le champ et la correction : corriger et
   reproposer.
2. Terminer le tour par la relecture : titre, mission, puis les lignes `relecture` de la
   proposition telles quelles (destinations et modes, sous-agents dans l'ordre, préparations dans
   l'ordre avec leurs options, fichiers, cadence), un aperçu de la consigne, l'identifiant de la
   proposition, et la question « Je crée cet agent ? ».
3. **Ne jamais appeler `creer` dans le tour de `proposer`.** Le code le refuse de toute façon :
   la création exige un message de l'utilisateur postérieur à la proposition, dans la même
   conversation. Si la réponse est ambiguë, ne pas créer. Une correction demandée donne une
   nouvelle proposition ; l'ancienne reste sans effet.
4. Après `creer`, donner le lien du job (`/jobs`) et rappeler que `retirer` arrête toute
   livraison. Lancer un run reste soumis à la confirmation de `compose_and_launch_job`.

## Faire tourner un agent

Un agent n'est pas un processus allumé : chaque run est un conteneur jetable qui va au bout puis
disparaît. Aucun agent n'a de cron à lui : avec une `cadence`, le seul cron des agents,
`run-agents`, enchaîne chaque matin préparations, run, sous-agents et livraison.

| Action | Garde |
|---|---|
| lire (configuration, runs, envois) | aucune |
| lancer un run maintenant | `proposer-lancement`, puis `lancer` au tour suivant, après le oui |
| modifier la configuration, la consigne ou la cadence | `proposer` avec le même slug (une modification), `creer` après le oui, `retirer` pour revenir en arrière |
| passer une destination en réel | jamais depuis la conversation : une PR sur `reel_autorise` |

```bash
python -m skills.agents.scripts.agents proposer-lancement --agent <slug>   # montre les préparations, ne lance rien
python -m skills.agents.scripts.agents lancer --agent <slug>               # tour suivant, après le oui de l'utilisateur
```

Le code refuse un `lancer` sans message ultérieur de l'utilisateur, et une confirmation ne sert
qu'une fois. Une préparation sans contenu (cron sans dernière sortie réussie, jeu S3 absent)
empêche le run.

## Livrer un run et relire ses productions

```bash
python -m skills.agents.scripts.agents livrer --agent <slug> --run <run_id>
python -m skills.agents.scripts.agents montrer-envoi --agent <slug> --envoi <id>
python -m skills.agents.scripts.agents approuver-envoi --agent <slug> --envoi <id>   # tour suivant, après le oui
```

`livrer` n'accepte qu'un run terminé du job de l'agent ; relivrer le même run n'écrit rien de
plus. Une seule destination hors liste fait refuser tout le run. Rendre compte de chaque envoi
(destination, mode, statut : `ombre`, `a_relire`, `envoyee`, `echec`, `ecarte` quand le
classificateur l'a jugée sous le seuil, `echec_sous_agent` quand un sous-agent a échoué : rien
n'est livré de cette production, et relancer `livrer` sur le même run la refait passer par ses
sous-agents) et le nombre d'appels aux sous-agents. Pour un envoi `a_relire`,
`montrer-envoi` puis afficher son titre et son texte, demander la validation, et n'appeler
`approuver-envoi` qu'au tour suivant. Un envoi `echec` se réessaie de la même façon.

## Fichiers de l'agent

```bash
python -m skills.agents.scripts.agents fichier --agent <slug> --nom <fichier> [--version <n>]
python -m skills.agents.scripts.agents historique --agent <slug> --nom <fichier>
python -m skills.agents.scripts.agents comparer --agent <slug> --nom <fichier> --de <n> --a <m>
python -m skills.agents.scripts.agents proposer-retour --agent <slug> --nom <fichier> --version <n>
python -m skills.agents.scripts.agents revenir --agent <slug> --nom <fichier>   # tour suivant, après le oui
```

Lire, l'historique et la comparaison sont libres : c'est ainsi que l'utilisateur consulte en
discutant ce que l'agent a écrit. `proposer-retour` montre la différence ; `revenir` écrit
l'ancienne version comme une version nouvelle (rien ne s'efface), seulement après un oui dans un
message ultérieur.

## Exemple : des tickets pour un backlog commun

Demande : « identifie des tickets à ajouter au backlog commun à partir du backlog (une base
Notion), des réflexions des bizdev (une page Notion) et du code (une organisation GitHub, en
commençant par un dépôt) ; un sous-agent `clef` dit pour chaque ticket s'il est quick-win, feature
ou verticale ; crée les tickets dans un fichier que je consulte ; laisse l'agent décider des
définitions et les faire évoluer ; deux fois par semaine ». Rien de cela n'est impossible :

```yaml
format: pdi.agent/1
slug: tickets-backlog
titre: Tickets pour le backlog commun
mission: Proposer des tickets pour le backlog commun à partir du backlog, des réflexions bizdev et du code.
points_de_contact: []
cadence:
  jours: [lundi, jeudi]
preparations:
  - type: notion
    base: 2715f321b60480e1827df1529ea754f1
    colonnes: [Nom, Statut, Étiquettes]
    regrouper_par: [Statut, Étiquettes]
  - type: notion
    page: 27d5f321b6048070985bc6cb1222230b
  - type: github
    depots: [gip-inclusion/les-emplois]
    organisation: gip-inclusion
outils_modeles:
  - type: classificateur
    modele: "clef:27b"
    etiquettes:
      - nom: quick-win
        question: Le ticket se réalise-t-il en moins d'une semaine, sans dépendance ?
      - nom: feature
        question: Le ticket décrit-il une fonctionnalité nouvelle pour les utilisateurs ?
      - nom: verticale
        question: Le ticket ouvre-t-il un nouveau public ou un nouveau métier ?
    seuil: 0.6
fichiers: [definitions.md, tickets.md]
```

La consigne dit à l'agent de lire `definitions.md` (vide au premier run), d'en rendre une version
revue après ses analyses, et de rendre chaque ticket comme un envoi vers `fichier:tickets.md` avec
une `cle` stable (un ticket repris le met à jour). Les noms des colonnes viennent de la base : si
l'un manque, la préparation le dit et liste les colonnes réelles. Ensuite : `fichier --nom
tickets.md` pour les consulter, `historique` et `comparer` pour voir ce qui a changé.
