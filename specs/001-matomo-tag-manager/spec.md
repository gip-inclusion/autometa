# Spécification de fonctionnalité : Intégration Matomo Tag Manager sur Autometa

**Branche** : `001-matomo-tag-manager`
**Créée le** : 2026-04-13
**Statut** : Brouillon
**Entrée** : Description utilisateur : "je veux pouvoir utiliser le tag manager de matomo sur notre site autometa et donc ajouter un script pour son utilisation. Attention je veux que ce soit une seule fois dans le code et le reste gérer par l'interface matomo et non à chaque fois dans le code"

## Clarifications

### Session 2026-04-13

- Q : Comment se comporte le chargement du conteneur dans les environnements non‑production ? → R : Aucun conteneur chargé par défaut hors prod ; activable en renseignant un ID dédié via variable d'environnement. Si la variable est absente ou vide, aucun script n'est injecté dans les pages.
- Q : Quel est le périmètre des pages qui chargent le conteneur ? → R : Uniquement les pages applicatives d'Autometa qui étendent `web/templates/base.html`. Les apps interactives servies sous `/interactive/` ne sont pas instrumentées.

## Scénarios utilisateur & Tests *(obligatoire)*

### User Story 1 - Instrumenter le site sans redéploiement (Priorité : P1)

En tant qu'équipe produit / analytics d'Autometa, je veux qu'un conteneur Matomo Tag Manager soit chargé sur toutes les pages du site, afin de pouvoir ajouter, modifier ou retirer des tags (pages vues, événements de clic, conversions, intégrations tierces) directement depuis l'interface Matomo Tag Manager, sans qu'un développeur ait à modifier le code ni à redéployer l'application à chaque nouvel événement à suivre.

**Justification de la priorité** : C'est le cœur de la demande. Sans ce socle, chaque nouvel événement analytique nécessite un ticket développeur + un déploiement, ce qui bloque l'itération côté produit/analytics.

**Test indépendant** : Publier une version du conteneur MTM qui contient un tag « page vue », naviguer sur Autometa et vérifier dans Matomo que les visites sont bien enregistrées — sans aucune modification de code entre la création du tag et son effet observable.

**Scénarios d'acceptation** :

1. **Étant donné** un conteneur MTM publié contenant uniquement un tag « page vue », **Quand** un utilisateur visite n'importe quelle page d'Autometa, **Alors** la visite apparaît dans les rapports Matomo du site Autometa.
2. **Étant donné** qu'une personne analytics ajoute un nouveau tag d'événement (ex. clic sur « Nouvelle conversation ») depuis l'interface MTM et publie une nouvelle version du conteneur, **Quand** un utilisateur déclenche cette action sur le site, **Alors** l'événement est enregistré dans Matomo sans aucune modification ni redéploiement du code d'Autometa.
3. **Étant donné** qu'une personne analytics désactive un tag existant depuis l'interface MTM et republie le conteneur, **Quand** l'action correspondante est réalisée sur le site, **Alors** plus aucun événement n'est remonté pour ce tag, sans intervention développeur.

---

### User Story 2 - Respect du consentement et de la vie privée (Priorité : P2)

En tant que responsable conformité, je veux que le chargement du conteneur et des tags respecte les règles applicables au site (RGPD, recommandations CNIL pour le secteur public), afin que la collecte analytique reste conforme.

**Justification de la priorité** : Autometa est opéré par un acteur public (GIP Inclusion) ; une collecte non conforme expose l'organisation. L'exigence est importante mais reste traitable après la pose du socle, car elle se configure dans MTM une fois le conteneur en place.

**Test indépendant** : Charger le site et vérifier que le comportement de collecte (exemption CNIL pour Matomo auto-hébergé ou bandeau de consentement) correspond au choix documenté pour Autometa.

**Scénarios d'acceptation** :

1. **Étant donné** la configuration de consentement retenue pour Autometa, **Quand** un visiteur arrive sur le site, **Alors** la collecte de données démarre ou est différée conformément à cette configuration.

---

### Cas limites

- **Serveur Matomo indisponible** : si le serveur qui sert le script du conteneur est injoignable (panne, latence réseau), le site Autometa continue de s'afficher et reste utilisable ; le chargement du conteneur ne doit jamais bloquer le rendu ni casser l'interface.
- **Bloqueur de traqueurs côté visiteur** : si une extension bloque le script, le site reste pleinement utilisable ; aucun événement n'est alors remonté — comportement attendu.
- **Environnement hors production** : le conteneur ne doit pas polluer les statistiques de production quand le site tourne en local ou en recette.
- **Interactions très précoces** : les interactions qui surviennent avant que le conteneur ait fini de se charger peuvent ne pas être captées — accepté.
- **Pas de nouvelle publication côté MTM** : tant qu'une nouvelle version du conteneur n'est pas publiée, le comportement sur le site reste celui de la dernière version publiée.

## Exigences *(obligatoire)*

### Exigences fonctionnelles

- **EF-001** : Autometa DOIT charger le conteneur Matomo Tag Manager sur toutes les pages applicatives qui héritent du template de base partagé (`web/templates/base.html`), publiques comme authentifiées. Les apps interactives servies sous `/interactive/` (générées par l'agent, indépendantes du template de base) NE SONT PAS dans le périmètre et ne chargent pas le conteneur.
- **EF-002** : Le chargement du conteneur DOIT être effectué à un seul endroit du code (point d'injection unique dans le template de base, mutualisé par toutes les pages applicatives). Ajouter, modifier ou supprimer un tag ou un événement NE DOIT PAS nécessiter de modification du code applicatif.
- **EF-003** : Une fois le conteneur en place, toute instrumentation analytique (pages vues, événements, variables, déclencheurs, intégrations tierces) DOIT pouvoir être gérée entièrement depuis l'interface Matomo Tag Manager.
- **EF-004** : Le chargement du conteneur NE DOIT PAS dégrader de manière perceptible l'expérience utilisateur (ni bloquer le rendu, ni retarder significativement l'interactivité de la page).
- **EF-005** : Une indisponibilité ou une erreur de chargement du conteneur NE DOIT PAS empêcher l'affichage ou l'utilisation normale du site.
- **EF-006** : Le chargement du conteneur DOIT être piloté par une variable d'environnement dédiée portant l'ID du conteneur. Si cette variable est absente ou vide, AUCUN script de conteneur ne DOIT être injecté dans les pages — c'est le comportement par défaut hors production. Renseigner l'ID dans un environnement non‑prod (recette, démo) DOIT y activer le chargement du conteneur correspondant.
- **EF-007** : L'identifiant du conteneur Matomo Tag Manager et l'URL du serveur Matomo DOIVENT être gérés comme de la configuration, jamais en dur dans le code applicatif.
- **EF-008** : Le comportement de collecte DOIT respecter la politique de consentement retenue pour Autometa (politique configurée côté Matomo / MTM).

### Entités clés

- **Conteneur MTM** : unité publiée depuis l'interface Matomo Tag Manager qui regroupe tags, déclencheurs et variables. Identifié par un ID de conteneur et versionné — seule la version publiée est exécutée sur le site.
- **Tag** : instrumentation individuelle (page vue, événement, appel tiers) définie et configurée dans MTM.
- **Déclencheur** : règle qui détermine quand un tag s'exécute (chargement de page, clic sur sélecteur, etc.), définie dans MTM.

## Modèle de menaces *(obligatoire — cf. constitution)*

### Actifs

- Les **pages d'Autometa** elles-mêmes (leur intégrité d'affichage et leur disponibilité) : un script tiers chargé sur toutes les pages peut, s'il est compromis ou mal configuré, affecter tout le site.
- Les **données de navigation des utilisateurs** collectées par les tags (URL visitées, éventuels clics, identifiants techniques) : une fois instrumentées, elles transitent vers le serveur Matomo.
- La **configuration du conteneur** dans l'interface MTM : qui peut y publier, avec quels privilèges.

### Acteurs malveillants

- Un utilisateur interne mal intentionné ou compromis ayant accès à l'interface MTM, qui pourrait publier un tag exfiltrant des données ou injectant du contenu dans les pages.
- Un attaquant externe ciblant le serveur Matomo auto-hébergé ou l'infrastructure qui sert le script de conteneur.
- Une extension navigateur malveillante côté visiteur (hors périmètre de contrôle, mais à garder en tête).

### Vecteurs d'attaque & Atténuations

| # | Vecteur d'attaque | Probabilité | Impact | Atténuation |
|---|-------------------|-------------|--------|-------------|
| 1 | Un tag malicieux publié depuis MTM exfiltre des données ou injecte du code sur toutes les pages d'Autometa | Basse | Haut | Accès à l'interface MTM restreint aux personnes habilitées ; revue des tags publiés ; conteneur dédié à Autometa pour limiter le périmètre |
| 2 | Compromission ou indisponibilité du serveur Matomo qui sert le script du conteneur | Basse | Moy | Chargement asynchrone / non bloquant ; site reste fonctionnel sans analytics ; supervision du serveur Matomo déjà en place |
| 3 | Fuite de l'identifiant de conteneur ou de l'URL Matomo via le code source côté client | Haute | Bas | Ces valeurs sont par nature publiques (elles sont lues par le navigateur) ; aucune donnée sensible ne doit dépendre de leur confidentialité |
| 4 | Collecte non conforme au consentement (tags déclenchés trop tôt, collecte de données exemptées) | Moy | Moy | Politique de consentement configurée dans MTM ; revue conformité avant chaque publication de conteneur sensible |

### Risque résiduel

- Le risque principal est la **gouvernance des publications MTM** : une fois le conteneur en place, la surface de changement se déplace du code vers l'interface Matomo. Accepté, à condition que les droits de publication sur le conteneur Autometa soient limités et tracés.
- Les indisponibilités ponctuelles du serveur Matomo n'affectent pas l'usage du site : risque accepté.

## Critères de succès *(obligatoire)*

### Résultats mesurables

- **CS-001** : 100 % des pages applicatives d'Autometa (héritant de `base.html`) servies à un utilisateur chargent le conteneur MTM après mise en production (vérifiable sur un échantillon représentatif de pages). Les apps interactives sous `/interactive/` sont explicitement hors périmètre de cette mesure.
- **CS-002** : L'équipe analytics peut ajouter un nouvel événement suivi et le voir remonter dans Matomo en moins de 30 minutes, sans aucune modification de code ni redéploiement d'Autometa.
- **CS-003** : Le temps de chargement perçu des pages principales n'augmente pas de plus de 5 % après la mise en place du conteneur.
- **CS-004** : Zéro incident de production (page blanche, erreur bloquante) imputable au chargement ou à l'indisponibilité du conteneur pendant les 30 jours suivant la mise en service.
- **CS-005** : Sur les 3 mois suivant la mise en service, ≤ 1 modification du code d'Autometa est nécessaire pour faire évoluer l'instrumentation analytique (hors évolutions du socle lui-même).

## Mesure d'impact *(obligatoire — cf. constitution)*

### Métriques de succès

| Métrique | Référence (actuel) | Cible | Méthode de mesure |
|----------|-------------------|-------|-------------------|
| Pages d'Autometa instrumentées (taux de couverture) | 0 % | 100 % | Inspection d'un échantillon de pages + rapports Matomo |
| Délai entre la demande d'un nouveau tag et sa mise en production | Plusieurs jours (cycle dev + déploiement) | < 30 min (publication MTM) | Mesure du temps écoulé entre création d'un tag dans MTM et première remontée d'événement en production |
| Nombre de modifications du code d'Autometa dédiées à l'ajout/retrait de tags, sur 3 mois glissants | Non mesuré (actuellement : chaque tag = un commit) | ≤ 1 | Revue de l'historique git sur les chemins des templates concernés |
| Incidents de production imputables au chargement du conteneur, sur 30 jours après mise en service | — | 0 | Supervision applicative et remontées utilisateurs |

### Cadence de revue

- Première revue : 30 jours après la mise en service, pour valider l'absence d'incident et la fluidité du workflow analytics.
- Revue suivante : 3 mois après la mise en service, pour mesurer la réduction effective des modifications de code liées au tracking.

## Hypothèses

- Autometa utilise une instance Matomo déjà opérationnelle (celle décrite dans le contexte projet) ; aucune nouvelle instance Matomo n'est à mettre en place dans le cadre de cette fonctionnalité.
- Un conteneur MTM dédié à Autometa peut être (ou a été) créé dans cette instance Matomo ; son identifiant sera fourni via configuration.
- Le conteneur est publié depuis l'interface Matomo par une personne habilitée ; le cycle de publication côté Matomo est hors périmètre de cette spécification.
- La politique de consentement (bandeau ou exemption CNIL pour un outil analytique auto-hébergé) est tranchée dans la configuration du conteneur, pas dans le code applicatif.
- Les environnements non‑production d'Autometa tournent par défaut sans conteneur chargé ; un conteneur de recette dédié peut être activé ponctuellement en définissant la variable d'environnement correspondante, sans toucher au code.
- Aucun tracking Matomo direct (`_paq`) n'est actuellement câblé en dur dans les templates d'Autometa ; la pose du socle MTM n'a donc pas à gérer une migration préalable. Une éventuelle future migration de code existant vers MTM reste hors périmètre de cette spécification.
