# Laisser un agent écrire dans Slack et dans Notion, dans une liste fermée

## Ce que je veux

Qu'un job d'Autometa devenu agent puisse déposer ce qu'il a produit dans un canal Slack ou une
base Notion de l'équipe, mais seulement là où on l'a autorisé, et d'abord sans rien envoyer : on
regarde ce qu'il aurait écrit, puis une personne relit chaque envoi, et l'envoi direct ne s'ouvre
qu'agent par agent, par une PR.

## Ce qui devra marcher

DOD-1 — La liste des destinations où un agent peut écrire est un fichier du dépôt : chaque
  destination a un identifiant et un canal (Slack ou Notion), et l'identifiant réel du canal ou de
  la base vit dans la configuration de l'instance, pas dans le dépôt.

DOD-2 — La configuration d'un agent (format `pdi.agent/1`, réduit aux champs dont ce parcours a
  besoin) est refusée, avec un message qui nomme le champ et la correction, quand elle cite une
  destination absente de la liste, un champ inconnu, un mode inconnu, ou un lien, une personne ou
  un canal dans le texte de sa mission.

DOD-3 — Quand une production d'agent vise une destination que sa configuration ne cite pas, ou
  qui n'est pas dans la liste, rien n'est écrit ni enregistré pour aucune des productions du même
  passage, et le refus nomme la destination.

DOD-4 — En mode ombre, une production est enregistrée pour être consultée, et rien n'est écrit
  dans Slack ni dans Notion.

DOD-5 — En mode relecture, une production est enregistrée « à relire » et rien n'est écrit tant
  qu'une personne ne l'a pas approuvée ; après approbation, elle est écrite une fois, et une
  seconde approbation n'écrit rien.

DOD-6 — Le mode réel n'est accepté que pour un agent nommé dans la liste des agents autorisés de
  la destination ; il écrit alors directement : un message dans le canal Slack, ou une page dans la
  base Notion.

DOD-7 — Une production Notion qui porte la même clé qu'une page déjà écrite par le même agent
  met à jour cette page au lieu d'en créer une seconde.

DOD-8 — Relancer la livraison d'un passage déjà livré n'écrit rien une seconde fois.

DOD-9 — Les journaux de l'application nomment l'agent, la destination, le mode et le statut de
  chaque production, jamais son titre ni son texte.

## Sources lues

- `lib/slack.py` — `post_message` poste déjà dans un canal avec le jeton du bot
  (`SLACK_BOT_TOKEN`) : réutilisé pour `DOD-6`.
- `lib/notion.py` — `notion_request`, `markdown_to_blocks` et la création de page de
  `publish_report` : réutilisés pour `DOD-6` et `DOD-7` ; aucune fonction ne met à jour le contenu
  d'une page existante.
- `lib/zendesk_changeset.py`, `paved-road/zendesk-write/` — enregistrement sur S3 sans table, et
  approbation dans un message ultérieur : le patron de `DOD-5`.
- `skills/compose_and_launch_job/SKILL.md` — un worker de job n'a aucun accès aux API
  d'Autometa : ce qu'il produit est livré par Autometa après le run, jamais par le worker, qui ne
  détient donc aucun jeton Slack ni Notion.

## Questions ouvertes

Aucune.

## Validation

En attente de validation par Alexis Akinyemi. Défauts retenus : une production refusée fait
refuser tout le passage ; pas de message privé Slack (aucune table personne vers identifiant) ;
les champs du format qui servent le socle de veille (signaux, paliers, budget, territoires,
cadence, lot, sources) reviendront avec le code qui les lit.
