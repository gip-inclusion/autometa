# Déclarer un agent de veille BOAMP par une PR

## Ce que je veux

Un premier agent réel, déclaré dans le dépôt et relu en PR : chaque semaine, il lit les avis de
marchés publics ouverts au BOAMP (open data de la DILA, sans compte ni jeton) et dépose dans un
canal Slack de l'équipe bizdev ceux qui touchent l'insertion professionnelle, l'IAE ou
l'accompagnement des bénéficiaires du RSA. Il commence en ombre : on regarde ce qu'il aurait
écrit avant qu'il écrive quoi que ce soit. Ajouter un agent, c'est ajouter un fichier relu en PR,
et la CI refuse un fichier faux.

## Ce qui devra marcher

DOD-1 — L'agent de veille BOAMP est un fichier de configuration `pdi.agent/1` du dépôt, accepté
  par le validateur, accompagné de la consigne de son job ; sa seule destination est le canal
  Slack bizdev de la liste fermée, en mode ombre.

DOD-2 — La consigne dit ce que l'agent lit : l'API publique du BOAMP, la fenêtre de parution, la
  règle de tri des avis (mots-clés autoportants, objet générique qualifié par un thème, lexique
  d'exclusion) et la forme du message ; elle ne cite aucune autre adresse que celles du BOAMP.

DOD-3 — La CI valide toutes les configurations d'agents du dépôt : un fichier qui cite une
  destination hors liste, demande le mode réel sans y être autorisé, porte un identifiant
  différent de son nom de fichier ou n'a pas de consigne fait échouer `make test` (couloir unit
  de la CI), avec un message qui nomme le fichier et la correction.

DOD-4 — L'agent du dépôt s'enregistre par le parcours de création existant (proposition, puis
  création après confirmation dans un message ultérieur) : sa proposition porte sa consigne et le
  contrat de sortie qui ne liste que sa destination.

DOD-5 — Un run de l'agent dont la sortie reprend des avis BOAMP est livré en ombre : l'envoi est
  enregistré et rien n'est écrit dans Slack ni dans Notion. Aucun test ne fait d'appel réseau, au
  BOAMP ni ailleurs.

## Sources lues

- `lib/agent_config.py`, `config/agent_destinations.yaml` (#277) — format réduit, liste fermée,
  `reel_autorise` : la destination `bizdev.marche` existe déjà, en Slack, sans agent autorisé en
  réel (`DOD-1`, `DOD-3`).
- `lib/agents.py`, `skills/agents/` (#278) — `plan` prend une configuration YAML et une consigne,
  ajoute le contrat de sortie ; réutilisé tel quel pour enregistrer l'agent du dépôt (`DOD-4`).
- `lib/agent_delivery.py` (#277) — mode ombre : enregistrement seul (`DOD-5`).
- `skills/compose_and_launch_job/SKILL.md` — le worker a `curl` et `python3`, aucun accès à
  Autometa : c'est lui qui interroge le BOAMP, la consigne doit être autosuffisante (`DOD-2`).
- API Explore v2.1 du jeu `boamp` (boamp-datadila.opendatasoft.com) — champs `idweb`, `objet`,
  `nomacheteur`, `code_departement`, `datelimitereponse`, `descripteur_libelle`, `type_marche`,
  `nature`, `etat`, `url_avis` et filtre `search(objet, …)`, vérifiés par une requête manuelle sur
  une semaine de parution (`DOD-2`).
- `~/pdi-agents-ref/` (`INTEGRATION_AUTOMETA.md`, `agents/exemples/`) — un agent à source publique
  est un fichier `agents/<slug>.yaml` arrivé par PR, gardé par une vérification en CI (`DOD-3`).
- Référence de veille BOAMP côté clawdio — l'idée de la règle à trois niveaux et du lexique
  d'exclusion, sans son périmètre ni ses seuils, propres à une autre structure (`DOD-2`).

## Questions ouvertes

Aucune.

## Validation

En attente de validation par Alexis Akinyemi. Défauts retenus : fichiers `agents/<slug>.yaml` et
`agents/<slug>.md` à la racine du dépôt ; vérification par un test de `make test` (déjà dans la CI
et le hook pre-commit) plutôt qu'un nouveau workflow ; fenêtre glissante de 7 jours et run lancé à la main chaque semaine
depuis `/jobs`, faute de planification dans le moteur de jobs ; pas de mémoire des avis déjà vus
entre deux runs ; le tag « agent » de #275 se pose sur le job une fois les deux PR fusionnées.
