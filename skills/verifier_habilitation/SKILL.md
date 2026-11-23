---
name: verifier_habilitation
description: Vérifier qu'une organisation qui demande l'habilitation sur La plateforme de l'inclusion (ex-Emplois) relève bien de la liste des prescripteurs habilités au national — à partir d'un ticket Zendesk « Vérification de l'habilitation », d'un identifiant d'organisation ou d'un SIRET, avec ou sans nom de domaine. Rend un verdict en trois lignes, le raisonnement et les sources, pour que le support décide dans l'admin. À utiliser dès qu'un membre du support demande de vérifier un SIRET, une organisation ou un ticket d'habilitation.
---

# Vérifier une habilitation

Le support de La plateforme reçoit, plusieurs fois par jour, un ticket Zendesk « Vérification de
l'habilitation d'une nouvelle organisation » (étiquette `zammadix_verification-habilitation`) : une
organisation vient de s'inscrire en se déclarant d'un type habilité. Le support valide ou refuse
l'habilitation dans l'admin. Ce skill prépare la décision ; il ne la prend pas, et n'écrit nulle part.

L'enjeu est réel : une habilitation donne le droit de prescrire des parcours IAE. Le support doit
pouvoir contrôler chaque affirmation : chaque fait cite sa source, chaque verdict son raisonnement.

## Entrées acceptées

- un numéro de ticket Zendesk ;
- un lien admin `…/prescribers/prescriberorganization/<id>/change/` ou un identifiant d'organisation ;
- un SIRET (14 chiffres, espaces tolérés), avec ou sans nom de domaine (`@exemple.fr`).

Un identifiant n'entre dans une requête que s'il est un entier, un SIRET que s'il fait 14 chiffres
(règles du skill `autometa_tables_db`).

## Méthode

1. **Ticket** (skill `zendesk`, lecture seule) : le premier commentaire donne l'identifiant de
   l'organisation (dans le lien admin) et le « Type sélectionné par l'utilisateur ». Le ticket ne
   contient ni SIRET ni domaine.
2. **Organisation sur La plateforme** (skill `autometa_tables_db`, table `organisations`) : SIRET,
   type déclaré, date d'inscription, statut d'habilitation. Les domaines e-mail de ses membres se
   lisent dans `utilisateurs` (par `id_organisation`) : n'en extraire que la partie après `@`, jamais
   l'adresse ni le nom. La table est mise à jour une fois par jour : une organisation créée le jour
   même peut manquer ; demander alors le SIRET.
3. **Établissement** : `python -m skills.verifier_habilitation.scripts.etablissement <SIRET>`
   interroge l'API publique Recherche d'entreprises — nom, activité (NAF), nature juridique (code
   INSEE), état administratif (ouvert ou fermé), indicateurs (association, FINESS, service public,
   collectivité), lien vers la fiche. Au besoin, l'annuaire https://annuaire.action-sociale.org et le
   site de la structure, lus avec WebFetch.
4. **Liste de référence** : l'article Zendesk Guide 14733442624657 « Liste des prescripteurs
   habilités au national », relu à chaque vérification (il est modifié de temps en temps). Citer la
   catégorie retenue par son libellé dans la liste, sans numéro inventé.
5. **Domaine** : lui appartient-il à la structure (site officiel, mentions légales, page contact) ?
   Une messagerie grand public (gmail.com, orange.fr, hotmail.fr, laposte.net…) ne prouve rien.

## Règles

- Ne jamais forcer une structure dans une catégorie. Pas dans la liste : « Non ». Indices
  contradictoires ou manquants : « Doute », avec la raison.
- La question est : **le type déclaré correspond-il à ce qu'est réellement l'établissement ?**
  Comparer le type déclaré aux faits (activité, forme juridique, site) et le dire quand ils divergent.
- Une habilitation préfectorale (organismes habilités par le préfet après avis du CDIAE) ne se
  vérifie pas sur les sources publiques : répondre « Doute » et orienter vers la DDETS du
  département.
- SIRET fermé, introuvable, ou qui ne correspond pas au nom de l'organisation : le signaler en tête.
- Phrases simples, sans numéro d'article de loi.
- Ne recopier dans la réponse ni nom, ni e-mail, ni téléphone d'une personne lus dans le ticket.

## Réponse

Toujours ce format, rien d'autre :

```
Structure : <nom> — <type d'établissement>, <ville> (<département>) — SIRET <siret>, <ouvert|fermé>
Domaine : ✅ Oui / ❌ Non / ❓ Impossible à vérifier — <raison en quelques mots>
Habilité : ✅ Oui (<libellé de la liste>) / ❌ Non / ❓ Doute — <raison en une phrase>

Raisonnement :
- Type déclaré sur La plateforme : <type> ; ce que montrent les sources : <…>
- <chaque fait utilisé, avec sa source entre crochets>

À vérifier par vous : <ce que le skill n'a pas pu établir, ou « rien »>

Sources : <liens cliquables : fiche Recherche d'entreprises, liste officielle, site de la structure, lien admin>
```

Une conversation par vérification ou par petit lot : ne pas prolonger le même fil sur des dizaines
de SIRET.
