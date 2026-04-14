# Spécification de fonctionnalité : Bouton drapeau de signalement dans la barre de chat

**Branche** : `002-flag-conversation`
**Créée le** : 2026-04-14
**Statut** : Brouillon
**Entrée** : Description utilisateur : "Ajoute un bouton drapeau dans la barre de chat permettant aux utilisateurs de signaler un problème dans une conversation. Les signalements sont visibles dans le dashboard /interactive/conversations-echecs/."

## Clarifications

### Session 2026-04-14

- Q : Qui peut consulter la liste des signalements et retirer un signalement (endpoints `GET /api/conversations/flagged` et `DELETE /api/conversations/:id/flag`) ? → R : Réservé aux utilisateurs listés dans `ADMIN_USERS`. Un non-admin qui tente d'accéder à ces endpoints (ou au dashboard) reçoit une réponse d'autorisation refusée.
- Q : Quelle est la longueur maximale acceptée pour la raison saisie par l'utilisateur ? → R : 500 caractères. Toute raison plus longue DOIT être rejetée par le backend avec une erreur de validation ; l'UI DOIT afficher un compteur ou équivalent pour prévenir l'utilisateur.

## Scénarios utilisateur & Tests *(obligatoire)*

### User Story 1 - Signaler un problème sur une conversation en cours (Priorité : P1)

En tant qu'utilisateur d'Autometa qui interagit avec l'assistant, je veux pouvoir marquer d'un drapeau une conversation dans laquelle je rencontre un problème (réponse fausse, plantage de l'agent, comportement inattendu, etc.), afin que l'équipe qui suit la qualité puisse prendre connaissance du cas et le traiter.

**Justification de la priorité** : C'est le cœur de la demande. Sans cette action côté utilisateur, le dashboard `/interactive/conversations-echecs/` (qui existe déjà et attend les données) reste vide et le circuit de remontée qualité ne fonctionne pas.

**Test indépendant** : Ouvrir une conversation existante, cliquer sur le bouton drapeau de la barre de chat, saisir (éventuellement) une courte raison, valider ; ouvrir le dashboard des conversations signalées et vérifier que la conversation y apparaît avec la bonne raison, l'identifiant utilisateur du signalant et un horodatage.

**Scénarios d'acceptation** :

1. **Étant donné** une conversation ouverte qui n'a pas encore été signalée, **Quand** l'utilisateur clique sur le bouton drapeau, saisit « la réponse est hors sujet » comme raison puis valide, **Alors** la conversation apparaît dans le dashboard des conversations signalées avec cette raison, l'identifiant de l'utilisateur signalant et l'horodatage du signalement.
2. **Étant donné** une conversation ouverte, **Quand** l'utilisateur clique sur le bouton drapeau puis valide sans saisir de raison, **Alors** la conversation est quand même signalée et apparaît dans le dashboard avec une raison vide.
3. **Étant donné** une conversation qui vient d'être signalée, **Quand** l'utilisateur revient sur la page de cette conversation, **Alors** le bouton drapeau indique visuellement que la conversation est déjà signalée (drapeau « rempli » plutôt que contour vide, ou équivalent).
4. **Étant donné** une conversation déjà signalée par l'utilisateur lui-même, **Quand** il clique à nouveau sur le bouton drapeau, **Alors** il peut retirer son signalement (toggle), et la conversation disparaît du dashboard.

---

### User Story 2 - Traiter les signalements depuis le dashboard (Priorité : P2)

En tant que membre de l'équipe qualité / produit, je veux voir la liste des conversations signalées, accéder rapidement à chacune, et retirer un signalement une fois le cas traité, afin de garder le dashboard à jour et de prioriser les cas restants.

**Justification de la priorité** : Le dashboard existe déjà (`data/interactive/conversations-echecs/`) et consomme deux endpoints (`GET /api/conversations/flagged` et `DELETE /api/conversations/:id/flag`). Cette user story couvre l'implémentation côté backend de ces endpoints ; sans eux, US1 reste invisible à l'équipe qualité.

**Test indépendant** : Avec au moins une conversation signalée en base, ouvrir le dashboard `/interactive/conversations-echecs/` et vérifier que la liste s'affiche. Cliquer sur « Retirer » pour une entrée et vérifier que la ligne disparaît et que la conversation n'est plus signalée côté utilisateur.

**Scénarios d'acceptation** :

1. **Étant donné** plusieurs conversations signalées en base, **Quand** un membre de l'équipe qualité ouvre le dashboard, **Alors** la liste affiche chaque conversation avec son titre (lien vers la conversation), l'identifiant de l'utilisateur signalant, la raison, l'horodatage, et un bouton « Retirer ».
2. **Étant donné** une conversation signalée visible dans le dashboard, **Quand** l'équipe qualité clique sur « Retirer », **Alors** le signalement est supprimé, la ligne disparaît du dashboard sans rechargement complet, et la conversation concernée n'est plus marquée comme signalée pour l'utilisateur.
3. **Étant donné** aucune conversation signalée, **Quand** le dashboard est ouvert, **Alors** un message « Aucune conversation signalée » s'affiche.

---

### Cas limites

- **Conversation partagée (lecture seule)** : un utilisateur qui consulte une conversation partagée par quelqu'un d'autre peut signaler un problème (c'est précisément un cas d'usage : quelqu'un a remarqué un souci dans une conversation publique). Le drapeau enregistré porte l'identifiant du signalant, pas du propriétaire de la conversation.
- **Signalement multiple** : une conversation donnée a au plus un seul signalement actif à un instant donné. Si un second utilisateur clique sur le drapeau d'une conversation déjà signalée, le signalement est mis à jour (dernière raison / dernier signalant l'emporte). Le cas « plusieurs signalements simultanés distincts » est explicitement hors périmètre v1 pour garder le modèle simple.
- **Retrait pendant le dashboard ouvert** : si deux membres de l'équipe qualité retirent le même signalement en quasi-simultané, la seconde action aboutit sans erreur (idempotent) mais la ligne a déjà disparu chez le premier ; aucun message d'erreur n'est nécessaire.
- **Conversation en cours de génération** : l'utilisateur peut signaler une conversation même pendant qu'une réponse de l'assistant est en train de s'afficher. Le signalement n'interrompt pas la génération.
- **Conversation supprimée** : si la conversation est supprimée après avoir été signalée, le signalement doit disparaître en même temps (pas d'entrée orpheline dans le dashboard).
- **Utilisateur non authentifié** : le bouton n'est pas affiché pour les visiteurs non authentifiés (la barre de chat elle-même l'est déjà pour les utilisateurs, donc c'est cohérent avec l'état actuel).

## Exigences *(obligatoire)*

### Exigences fonctionnelles

- **EF-001** : Sur toute page affichant une conversation (actuellement sous `/explorations/<id>`), la barre de chat DOIT afficher un bouton « drapeau » permettant de signaler la conversation. Le bouton DOIT être visible aussi bien sur les conversations interactives de l'utilisateur que sur les conversations partagées en lecture seule.
- **EF-002** : Quand l'utilisateur active le bouton drapeau, l'interface DOIT lui permettre de saisir une raison textuelle (facultative, **longueur maximale 500 caractères**) avant de confirmer le signalement. L'UI DOIT signaler visuellement la limite (compteur ou équivalent) et le backend DOIT rejeter toute raison dépassant 500 caractères avec une erreur de validation.
- **EF-003** : Une fois le signalement confirmé, le système DOIT enregistrer la conversation comme signalée, avec : l'identifiant de l'utilisateur signalant, la raison saisie (éventuellement vide) et la date/heure du signalement.
- **EF-004** : Le bouton drapeau DOIT refléter visuellement l'état courant du signalement — non signalée (drapeau vide) vs. signalée (drapeau rempli) — y compris au rechargement de la page.
- **EF-005** : Un utilisateur DOIT pouvoir retirer un signalement actif en cliquant à nouveau sur le bouton drapeau d'une conversation déjà signalée.
- **EF-006** : Une conversation a au plus **un seul** signalement actif à la fois. Signaler une conversation déjà signalée remplace le signalement précédent (raison, signalant, horodatage sont mis à jour).
- **EF-007** : Le dashboard `/interactive/conversations-echecs/` DOIT afficher la liste des conversations actuellement signalées, chacune avec son titre cliquable (lien vers la conversation), l'identifiant du signalant, la raison, l'horodatage, et une action permettant de retirer le signalement. L'accès au dashboard et aux endpoints de listage/retrait (`GET /api/conversations/flagged`, `DELETE /api/conversations/:id/flag`) DOIT être restreint aux utilisateurs administrateurs (liste `ADMIN_USERS`). Un non-admin qui y accède reçoit une réponse d'autorisation refusée.
- **EF-008** : Le retrait d'un signalement depuis le dashboard DOIT être idempotent — retirer un signalement déjà retiré ne provoque pas d'erreur.
- **EF-009** : La suppression d'une conversation DOIT entraîner la suppression du signalement associé (pas d'entrée orpheline dans le dashboard).
- **EF-010** : Les signalements enregistrés DOIVENT être conservés tant que la conversation existe et que personne ne les a retirés ; il n'y a pas d'expiration automatique.

### Entités clés

- **Signalement de conversation** : unité d'information représentant le fait qu'une conversation a été marquée comme problématique. Attributs : référence à la conversation (1–1), identifiant de l'utilisateur signalant (texte libre, e-mail ou identifiant de session selon la convention du projet), raison textuelle courte (peut être vide), date/heure du signalement. Au plus un signalement actif par conversation.
- **Conversation** (existante, pas créée par cette feature) : entité déjà présente dans le système ; l'unique ajout conceptuel est la possibilité d'avoir un signalement associé.

## Modèle de menaces *(obligatoire — cf. constitution)*

### Actifs

- **Les signalements eux-mêmes** : ils contiennent potentiellement du texte libre saisi par l'utilisateur. Ce texte est affiché dans le dashboard interne.
- **L'identifiant de l'utilisateur signalant** : donnée personnelle (e-mail ou identifiant) exposée au sein du dashboard qualité.
- **Les conversations concernées** : le fait qu'une conversation soit signalée est en soi une information sensible — elle suggère qu'il y a eu un problème.

### Acteurs malveillants

- Un utilisateur authentifié malintentionné qui injecterait du contenu hostile (XSS, contenu choquant) dans le champ « raison ».
- Un utilisateur qui spammerait des signalements (ex. script automatisé) pour pourrir le dashboard.
- Un utilisateur qui voudrait retirer ou falsifier les signalements d'autrui pour masquer des problèmes.

### Vecteurs d'attaque & Atténuations

| # | Vecteur d'attaque | Probabilité | Impact | Atténuation |
|---|-------------------|-------------|--------|-------------|
| 1 | Injection XSS via le champ « raison » rendu dans le dashboard | Moy | Moy | Échappement HTML systématique à l'affichage (le dashboard existant utilise déjà `escapeHtml`). Limite de longueur côté backend fixée à 500 caractères. |
| 2 | Spam de signalements par un utilisateur ou un script | Basse | Bas | Un seul signalement actif par conversation (EF-006) ; nombre de conversations accessibles par utilisateur limité en pratique ; pas de volume de stockage critique. |
| 3 | Signalement d'une conversation non accessible à l'utilisateur (écriture sur une conversation d'un autre utilisateur sans y avoir accès) | Basse | Moy | L'endpoint de signalement DOIT vérifier que l'utilisateur peut accéder à la conversation (même règle que la vue actuelle d'une conversation). |
| 4 | Retrait non autorisé d'un signalement depuis l'API | Moy | Bas | Le retrait passe par le dashboard `/interactive/`, qui est déjà protégé au même niveau que les autres pages internes d'Autometa ; le backend vérifie la même règle d'accès que pour le signalement. |
| 5 | Exposition de l'identifiant utilisateur du signalant à un tiers non autorisé | Basse | Bas | L'identifiant n'est visible que dans le dashboard `/interactive/conversations-echecs/`, lui-même servi par Autometa avec les mêmes protections que le reste de l'app. |

### Risque résiduel

- Le principal risque résiduel est **l'usage humain du dashboard** : le texte saisi par les utilisateurs peut contenir du contenu désagréable. C'est accepté — c'est précisément le rôle d'un canal de signalement de remonter ce type de contenu à l'équipe qualité, qui est adulte et préparée.
- La concurrence entre « plusieurs utilisateurs qui signalent la même conversation en même temps » aboutit à un « dernier gagne » silencieux : accepté (modèle volontairement simple).

## Critères de succès *(obligatoire)*

### Résultats mesurables

- **CS-001** : Un utilisateur peut passer de « voir un problème dans une conversation » à « signalement enregistré » en moins de **15 secondes** (ouvrir le drapeau, saisir éventuellement une raison, valider, confirmation visible).
- **CS-002** : Le dashboard des conversations signalées affiche tout nouveau signalement au plus **1 minute** après sa création (temps perçu = temps de rechargement du dashboard).
- **CS-003** : Sur les 3 premiers mois après lancement, au moins **80 % des signalements** comportent une raison non vide (indicateur que le parcours est compréhensible — sinon le champ « raison » est un frein ou mal placé).
- **CS-004** : L'équipe qualité traite (retire du dashboard) au moins **70 % des signalements reçus** dans les 30 jours suivant leur création — indicateur que le canal est utilisé utilement et pas submergé.
- **CS-005** : Zéro incident de type injection ou fuite d'information lié au champ « raison » pendant les 90 jours suivant le lancement.

## Mesure d'impact *(obligatoire — cf. constitution)*

### Métriques de succès

| Métrique | Référence (actuel) | Cible | Méthode de mesure |
|----------|-------------------|-------|-------------------|
| Nombre de signalements reçus / semaine | 0 (canal inexistant) | > 0 à M+1 ; cadence stable à M+3 | Compteur en base, revue hebdomadaire |
| Part des signalements avec raison non vide | N/A | ≥ 80 % à M+3 | Requête sur les signalements stockés |
| Délai moyen entre signalement et retrait (traitement) | N/A | ≤ 7 jours à M+1, ≤ 3 jours à M+3 | Différence entre `flagged_at` et date de suppression (à logger si besoin) |
| Taux d'utilisateurs distincts ayant utilisé le drapeau au moins une fois sur 3 mois | 0 | ≥ 20 % des utilisateurs actifs | Nombre d'utilisateurs distincts ayant un signalement actif ou historique sur la période |
| Incidents de contenu problématique non maîtrisés remontés par le drapeau | N/A | 0 (aucun incident lié à l'absence de canal) | Retours qualitatifs de l'équipe qualité |

### Cadence de revue

- **M+1** après la mise en service : vérifier que le flux fonctionne (au moins un signalement traité de bout en bout) et qu'il n'y a pas de friction évidente sur le parcours utilisateur.
- **M+3** : revoir les taux cibles (raison renseignée, traitement), ajuster l'ergonomie si besoin (rendre la raison obligatoire, ajouter des motifs pré-remplis, etc.).

## Hypothèses

- Le dashboard `/interactive/conversations-echecs/` existe déjà dans `data/interactive/` et consomme des endpoints `GET /api/conversations/flagged` (liste) et `DELETE /api/conversations/:id/flag` (retrait). Ces endpoints n'existent pas encore côté backend ; leur implémentation fait partie de cette feature.
- L'identifiant d'utilisateur utilisé est celui déjà en place dans Autometa (e-mail transmis par l'oauth-proxy ou utilisateur par défaut en local).
- Le modèle « un seul signalement actif par conversation » est volontairement simple pour la v1. Si le besoin émerge de gérer plusieurs signalements par conversation (plusieurs utilisateurs distincts, historique), ce sera une évolution ultérieure hors périmètre.
- Toute personne ayant accès à une conversation (propriétaire ou visionneuse d'une conversation partagée) peut la signaler. L'accès en lecture seule ne doit pas empêcher le signalement — au contraire, c'est un cas d'usage légitime.
- Le dashboard `/interactive/conversations-echecs/` et les endpoints qu'il consomme sont réservés aux administrateurs d'Autometa (liste `ADMIN_USERS`). C'est un ajout de contrôle d'accès spécifique à cette feature, justifié par la sensibilité des données exposées (identifiants des signalants + descriptifs potentiellement nominatifs).
- Le champ « raison » est volontairement facultatif en v1. Un objectif de ≥ 80 % de raisons renseignées (CS-003) évaluera si l'UX pousse suffisamment à remplir ce champ ; si non, la feature évoluera (raison obligatoire ou pré-suggérée) dans une itération ultérieure.
