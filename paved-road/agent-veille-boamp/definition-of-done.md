# Déclarer un agent de veille BOAMP par une PR

## Ce que je veux

Un premier agent réel, déclaré dans le dépôt et relu en PR : chaque semaine, il lit les avis de
marchés publics ouverts au BOAMP (open data de la DILA, sans compte ni jeton) et dépose dans un
canal Slack de l'équipe bizdev ceux qui touchent l'insertion professionnelle, l'IAE ou
l'accompagnement des bénéficiaires du RSA. Il commence en ombre. Ajouter un agent, c'est ajouter
un fichier relu en PR, et la CI refuse un fichier faux.

Révision du 05/11 : l'agent devient l'exemple de référence d'un agent composé uniquement des
briques génériques de #277 et #278 (préparations, sous-agents, cadence, fichiers de l'agent).
Aucune règle ni aucun appel réseau propres au BOAMP ne vivent dans le code.

## Ce qui devra marcher

DOD-1 — L'agent est un fichier `pdi.agent/1` du dépôt accepté par le validateur, composé de
  briques génériques : trois préparations `url` sur l'export public du BOAMP qui couvrent les sept
  jours complets précédant le run, un classificateur `clef:27b` en filtre puis en étiquettes (les
  deux rubriques), un fichier de l'agent `regles.md`, la cadence `jours: [lundi]` ; sa seule
  destination est le canal Slack bizdev, en ombre.

DOD-2 — La consigne n'appelle aucune API : elle lit son entrée et `regles.md`, et demande un
  envoi par avis retenu. Les termes, les exclusions et les rubriques vivent dans `regles.md`, que
  l'agent fait évoluer en rendant une version entière. Ni la consigne ni les règles ne portent de
  tiret long.

DOD-3 — La CI valide toutes les configurations d'agents du dépôt et la valeur initiale de leurs
  fichiers (`agents/<slug>/<nom>`) : une destination hors liste, le mode réel non autorisé, un
  identifiant différent du nom de fichier, une consigne absente, une valeur initiale d'un fichier
  non déclaré ou trop longue font échouer `make test`, avec un message qui nomme le fichier.

DOD-4 — L'agent du dépôt s'enregistre par le parcours de création existant ; la proposition
  porte la valeur initiale de `regles.md` (relue avec le reste), qui devient la version 1 du
  fichier à la création et n'écrase jamais un fichier que l'agent a déjà écrit.

DOD-5 — Un run simulé (export BOAMP et Ollama Cloud mockés au niveau HTTP) donne au worker les
  trois CSV puis `regles.md`, et sa sortie est livrée en ombre, un envoi par avis : un avis sous le
  seuil du filtre est écarté avec sa probabilité, les autres portent leurs étiquettes, une nouvelle
  version de `regles.md` est rangée ; rien n'est écrit dans Slack ni dans Notion.

DOD-6 — Le cron générique `run-agents` lance l'agent le lundi et pas un autre jour.

DOD-7 — Un point de contact peut regrouper ses productions (`regroupement: digest`, unitaire par
  défaut, sans changement pour les agents existants) : après les sous-agents, les productions
  retenues d'un run forment un seul envoi par destination, titré par la date du run et les
  nombres retenus et écartés, en sections par étiquette (puis « Autres »), une ligne par
  production avec son lien, dans un ordre déterministe et sous un plafond de taille qui dit le
  nombre de lignes omises. Les productions écartées restent tracées une par une ; relivrer le run
  ne refait ni ne renvoie le digest. L'agent BOAMP livre en digest.

## Sources lues

- `lib/agent_config.py`, `config/agent_destinations.yaml`, `config/agent_modeles.yaml`,
  `config/agent_preparations.yaml` : le format, la liste fermée, les sous-agents et les types de
  préparation permis (`DOD-1`).
- `lib/agent_connectors/url.py` : une adresse https publique, lue en texte, refusée au-delà de
  dix fois le plafond en octets, coupée au plafond en caractères (`DOD-1`, `DOD-5`).
- `lib/agent_subagents.py`, `lib/agent_delivery.py` : filtre qui arrête la chaîne sous le seuil
  (`ecarte`), étiquettes qui n'écartent rien (`DOD-5`).
- `lib/agent_files.py`, `lib/agents.py` : fichiers versionnés, donnés au run, réécrits par la
  sortie ; aucune valeur initiale avant cette PR, d'où `proposer --fichier` (`DOD-4`).
- API Explore v2.1 du jeu `boamp`, jouée à la main le 05/11/2026 en lecture seule :
  - `dateparution>=now(days=-8) and dateparution<now(days=-1)` rend exactement les sept jours qui
    précèdent la date du run (du 29/10 au 04/11 ce jour-là), quelle que soit l'heure : d'un lundi à
    l'autre, ni trou ni chevauchement ;
  - l'export CSV (`/exports/csv`) n'a pas la limite de 100 lignes de `/records` ;
  - avis de marché ouverts (`nature="APPEL_OFFRE"`, `etat="INITIAL"`) sur un an : services
    médiane 800 par semaine, maximum 1 092 ; fournitures médiane 322, maximum 461 ; environ 205
    caractères par avis avec les colonnes choisies ;
  - les trois URL de la configuration, passées par le vrai connecteur `url` : 97 879, 60 974 et
    50 487 caractères, aucune troncature (découpe de ce jour-là : lundi à jeudi puis vendredi à
    dimanche ; la configuration retenue coupe lundi à mercredi puis jeudi à dimanche pour garder
    de la marge au pic).

## Limites connues

- Une préparation coupée au plafond le dit à la fin de son contenu ; au-delà d'environ 975 avis
  de services sur une moitié de semaine, les derniers avis (date limite la plus lointaine) ne sont
  pas lus. Jamais atteint sur l'année écoulée.
- La fenêtre suppose un run le jour prévu ; un run relancé un autre jour lit les sept jours qui
  le précèdent.
- Pas de mémoire des avis déjà vus entre deux runs : la fenêtre glissante l'évite.

## Questions ouvertes

Aucune.

## Validation

En attente de validation par Alexis Akinyemi.
