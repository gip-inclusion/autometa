# Rédiger un ticket du backlog depuis le chat d'autometa

## Ce que je veux

Dans le chat d'autometa, je colle des notes, un vocal transcrit, un fil Slack ou un lien Figma,
et je demande un ticket. L'agent me propose un ticket court du Backlog unifié : un titre, un
paragraphe d'ouverture marqué `:autometa:`, puis Périmètre, Attendu, À trancher, Pistes
techniques évoquées et Sources. Il recommande l'équipe, le statut, le type, l'épic et la
propriété où m'inscrire, et me pose au plus trois questions. Il lit la maquette Figma. Il ne crée
le ticket qu'après mon accord.

## Ce qui devra marcher

DOD-1 — Un lien Figma vers un cadre donne, pour chaque cadre, son nom, ses textes visibles et une
image que l'agent peut regarder ; un lien sans cadre précis n'est pas lu, et l'agent le dit.

DOD-2 — Le contexte des équipes (équipes produit actives, épics actifs, titres de tickets récents)
est rangé chaque jour, et relu dans Notion s'il a plus d'un jour.

DOD-3 — Les tickets proches d'un titre proposé sont retrouvés et classés ; l'auteur est inscrit dans
`POM`, `UX`, `Développeurs` ou `Contributeurs` selon son rôle et l'équipe destinataire.

DOD-4 — Le ticket créé porte le titre, le corps, l'équipe, le statut, le type, l'épic et la
maquette ; jamais Priorité, Période ni Estimation ; un statut d'avancement de développement
(Ce sprint, En cours, En prod…) est refusé.

DOD-5 — Rien n'est écrit dans Notion sans `--go` : sans lui, le script montre seulement ce qui
serait créé.

## Décisions (validées le 2026-10-30)

1. Le marqueur `:autometa:` devient l'emoji personnalisé de l'espace. Essai du 2026-10-30 dans une
   page bac à sable : l'API accepte la mention `custom_emoji` dans un texte.
2. Âge maximal du contexte rangé avant relecture dans Notion : un jour.
3. Un ticket proche est signalé quand son titre partage au moins la moitié des mots-clés du titre
   proposé, et au moins deux ; l'agent ne montre que ceux qu'il juge vraiment proches. Mesuré le
   2026-10-30 sur 150 titres du backlog : 37 % ont au moins un candidat, contre 66 % avec « deux
   mots en commun ».
4. Maquette : 6 cadres au plus, images de 1 600 pixels de large au plus.
5. Auteur absent de l'Annuaire : l'agent lui demande son rôle. Sans compte Notion : le ticket est
   créé sans auteur inscrit, et l'agent le dit.

## Validation

Validé par LJ le 2026-10-30.
