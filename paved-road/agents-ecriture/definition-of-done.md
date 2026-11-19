# Laisser un agent écrire dans Slack et dans Notion, dans une liste fermée

> Révision 2026-11-19 — restauration des comportements natifs d'Autometa (demande d'Alexis
> Akinyemi) : la liste fermée du dépôt, `AGENT_DESTINATION_TARGETS`, `AGENT_SLACK_BOT_TOKEN` et
> `autonomous_allowed` disparaissent. Les droits qui bornent un agent sont ceux des connecteurs
> d'Autometa : les canaux où son application Slack est membre, les bases et pages partagées avec son
> intégration Notion. La cible est fixée dans la configuration de l'agent, confirmée en
> conversation. DOD-1, DOD-2, DOD-6, DOD-10 et DOD-11 sont révisés ; DOD-12 et DOD-13 sont ajoutés.

## Ce que je veux

Qu'un job d'Autometa devenu agent puisse déposer ce qu'il a produit dans un canal Slack ou une
base Notion de l'équipe, mais seulement là où on l'a autorisé, et d'abord sans rien envoyer : on
regarde ce qu'il aurait écrit, puis une personne relit chaque envoi, et l'envoi direct ne s'ouvre
qu'agent par agent, par une PR.

## Ce qui devra marcher

> Après la revue de #277 (§ 4) : les modes ombre, relecture et réel s'appellent `background`,
> `conversational` et `autonomous`, trois préréglages de `{can_publish, review_required}` ;
> `reel_autorise` devient `autonomous_allowed`. Les critères ci-dessous gardent leur sens.

DOD-1 — [Révision 2026-11-19 — plus de liste fermée dans le dépôt] Une destination d'agent se
  déclare dans sa configuration : un nom court, un canal (Slack ou Notion) et une cible (canal
  Slack par identifiant ou nom, base ou page Notion par lien ou identifiant). Tout canal où
  l'application Slack d'Autometa est membre, toute base ou page partagée avec son intégration Notion
  est une cible valide, sans PR ni réglage de l'instance.

DOD-2 — La configuration d'un agent (format `pdi.agent/1`, réduit aux champs dont ce parcours a
  besoin) est refusée, avec un message qui nomme le champ et la correction, quand elle cite une
  destination absente de la liste, un champ inconnu, un mode inconnu, ou un lien, une personne ou
  un canal dans le texte de sa mission.
  Révision 2026-11-19 — « absente de la liste » devient : une destination sans canal connu, avec
  une cible mal formée, ou sans cible dans un mode qui publie ; la relecture de la proposition
  affiche la cible de chaque destination.

DOD-3 — Quand une production d'agent vise une destination que sa configuration ne cite pas, ou
  qui n'est pas dans la liste, rien n'est écrit ni enregistré pour aucune des productions du même
  passage, et le refus nomme la destination.

DOD-4 — En mode ombre, une production est enregistrée pour être consultée, et rien n'est écrit
  dans Slack ni dans Notion.

DOD-5 — En mode relecture, une production est enregistrée « à relire » et rien n'est écrit tant
  qu'une personne ne l'a pas approuvée ; après approbation, elle est écrite une fois, et une
  seconde approbation n'écrit rien.

DOD-6 — [Révision 2026-11-19 — le mode réel s'ouvre par la confirmation de l'utilisateur, plus
  par une PR] Le mode réel écrit directement : un message dans le canal Slack, ou une page dans la
  base Notion (ou sous la page) ; les colonnes de la base dont le nom dit un champ de l'envoi (clé,
  étiquettes, lien, date) sont remplies. Une base ou page non partagée avec l'intégration est un
  échec qui le dit.

DOD-7 — Une production Notion qui porte la même clé qu'une page déjà écrite par le même agent
  met à jour cette page au lieu d'en créer une seconde.

DOD-8 — Relancer la livraison d'un passage déjà livré n'écrit rien une seconde fois.

DOD-9 — Les journaux de l'application nomment l'agent, la destination, le mode et le statut de
  chaque production, jamais son titre ni son texte.

DOD-10 — [Révision 2026-11-19 — plus de bot dédié aux agents] Un message Slack d'agent part avec
  l'application Slack d'Autometa, seulement dans un canal dont elle est membre : sinon l'écriture est
  enregistrée en échec avec un message qui demande de l'inviter. Si l'application peut écrire hors
  de ses canaux (`chat:write.public`) sans pouvoir les lister, l'envoi est refusé. Sans son jeton,
  l'écriture est enregistrée en échec avec un message qui le nomme. Les modes ombre et relecture
  n'en ont pas besoin pour enregistrer.

DOD-11 — [Révision 2026-11-19 — sans objet : il n'y a plus de liste ni d'identifiants réels à
  aligner au démarrage] L'application démarre sans rien vérifier des destinations d'agents ; une
  cible inaccessible est un échec de l'envoi concerné, qui le dit (DOD-6, DOD-10).

DOD-12 — [Révision 2026-11-19, ajout] La cible d'une destination est celle de la configuration :
  une production qui vise une autre destination, ou qui porte un champ de cible, fait refuser tout
  le passage, et un texte lu pendant le run qui demande d'écrire ailleurs ne change pas la cible.

DOD-13 — [Révision 2026-11-19, ajout] En rejouant l'export du 19/11 (un agent de veille qui marche,
  puis « pousse les news dans Slack via l'application Autometa et alimente cette base Notion »),
  l'agent écrit dans la base et dans le canal par une simple modification proposée puis confirmée
  dans la conversation, sans PR, sans variable d'instance, sans bot dédié.

## Sources lues

- `lib/slack.py` — `post_message` poste déjà dans un canal avec le jeton du bot
  passé en argument : réutilisé pour `DOD-6`, avec le jeton du bot des agents (`DOD-10`).
- `lib/notion.py` — `notion_request`, `markdown_to_blocks` et la création de page de
  `publish_report` : réutilisés pour `DOD-6` et `DOD-7` ; aucune fonction ne met à jour le contenu
  d'une page existante. Le jeton Notion est lu dans le module, pas passé en argument : un jeton
  Notion propre aux agents demanderait de le faire passer par toutes ces fonctions, hors périmètre.
- `lib/zendesk_changeset.py`, `paved-road/zendesk-write/` — enregistrement sur S3 sans table, et
  approbation dans un message ultérieur : le patron de `DOD-5`.
- `skills/compose_and_launch_job/SKILL.md` — un worker de job n'a aucun accès aux API
  d'Autometa : ce qu'il produit est livré par Autometa après le run, jamais par le worker, qui ne
  détient donc aucun jeton Slack ni Notion.

Attestations de la révision 2026-11-19 : `tests/test_agent_config.py` (DOD-1, DOD-2),
`tests/test_agent_delivery.py` (DOD-6, DOD-10, DOD-12), `tests/test_slack.py` (DOD-10),
`tests/test_agents.py::test_replaying_the_export_of_19_11_the_agent_writes_with_autometa_connectors_without_pr_or_setting`
(DOD-13).

## Questions ouvertes

Aucune.

## Validation

En attente de validation par Alexis Akinyemi. Défauts retenus : une production refusée fait
refuser tout le passage ; pas de message privé Slack (aucune table personne vers identifiant) ;
les champs du format qui servent le socle de veille (signaux, paliers, budget, territoires,
cadence, lot, sources) reviendront avec le code qui les lit.
