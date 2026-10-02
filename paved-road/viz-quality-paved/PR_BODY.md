<!-- Titre proposé : Vérifier la qualité visuelle d'un tableau de bord avant d'en partager le lien (parcours paved road) -->

## Ce que je voulais

Que l'agent regarde un tableau de bord comme le ferait un utilisateur avant d'en donner le lien — page
sans erreur, graphiques vraiment dessinés, aucune valeur cassée — et corrige avant de partager.

## Ce qui devait marcher

Sortie de `make paved-road-status` au commit `da763cb` :

| Critère | Ce qui devait marcher | Verdict | Preuve |
|---|---|---|---|
| DOD-1 | Un tableau de bord sain obtient « réussi », sans qu'Autometa soit démarré | démontré | `paved-road/viz-quality-paved/attestations/DOD-1.md` |
| DOD-2 | Une erreur JavaScript ou console fait échouer, message cité | démontré | `paved-road/viz-quality-paved/attestations/DOD-2.md` |
| DOD-3 | Un fichier non chargé (données, script, style) fait échouer, fichier nommé | démontré | `paved-road/viz-quality-paved/attestations/DOD-3.md` |
| DOD-4 | Un graphique sans tracé, ou moins de graphiques qu'attendu, fait échouer | démontré | `paved-road/viz-quality-paved/attestations/DOD-4.md` |
| DOD-5 | « NaN », « undefined », « null », « [object Object] » à l'écran font échouer | démontré | `paved-road/viz-quality-paved/attestations/DOD-5.md` |
| DOD-6 | Débordement horizontal à 1280 px, ou page sans texte, fait échouer | démontré | `paved-road/viz-quality-paved/attestations/DOD-6.md` |
| DOD-7 | Les consignes de création / modification imposent la vérification avant le lien | non démontré | — |
| DOD-8 | Le tag manager Matomo n'est jamais chargé : aucune fausse visite | démontré | `paved-road/viz-quality-paved/attestations/DOD-8.md` |
| DOD-9 | Les données en direct sortent en avertissement *(révisé le 2026-09-18)* | démontré | `paved-road/viz-quality-paved/attestations/DOD-9.md` |
| DOD-10 | Bloc d'erreur affiché ou « Chargement… » bloqué fait échouer | démontré | `paved-road/viz-quality-paved/attestations/DOD-10.md` |
| DOD-11 | Un tableau de bord sans page d'accueil échoue proprement | démontré | `paved-road/viz-quality-paved/attestations/DOD-11.md` |
| DOD-12 | Une page qui ne finit pas de charger en 30 s donne « délai dépassé » | démontré | `paved-road/viz-quality-paved/attestations/DOD-12.md` |
| DOD-13 | Pas de faux positifs (pas de minimum par défaut, onglets cachés, mots entiers, dédoublonnage) | démontré | `paved-road/viz-quality-paved/attestations/DOD-13.md` |
| DOD-14 | La vérification fonctionne en production | non démontré | — |

Chaque preuve joue à la fois les tests unitaires hermétiques (le jugement) et des tests dans un vrai
Chromium sur des tableaux de bord de test servis localement (le rendu), sans application démarrée.

## Ce qui n'a pas été démontré

- **DOD-7** — c'est une consigne donnée à l'agent (skills `create_dashboard`, `update_dashboard`,
  `verify_dashboard`, et `AGENT.md`) : aucun programme ne sait dire si un texte de consigne est
  suivi. À juger à la lecture de ces consignes, puis à l'usage.
- **DOD-14** — l'image de production embarque désormais Chromium (`Dockerfile`) et Playwright devient
  une dépendance d'exécution. Le job « Image » de la CI construit l'image, donc l'installation ; mais
  aucune preuve locale ne lance la vérification *dans* l'image. À constater sur la review app ou
  en staging.
- **Passage de l'état `build` à `prove`** : bloqué par le diagnostic d'environnement (famille B) —
  ce poste n'a ni `.env` ni Postgres / Redis / MinIO démarrés. Les preuves ne dépendent pas de ces
  services ; `make lint`, `make security` et `make test` passent (vérifiés par `make paved-road-checks`).
- Interface inchangée : rien à signaler au relecteur au sujet du smoke.

## Pour juger sans lire le code

- **Review app** : base vide — il n'y a aucun tableau de bord à regarder. La fonctionnalité se juge
  en demandant à l'agent de créer un tableau de bord et en regardant s'il lance la vérification
  avant de donner le lien.
- **Captures du smoke** : sans objet, aucune interface touchée.
- **Relecture `design-coherence`** — trois passes, détail dans
  `paved-road/viz-quality-paved/lentille.md` :
  - passe 1 : deux bloqueurs. Un graphique Chart.js ou Plot vide dessine quand même ses axes et
    passait pour tracé → corrigé, le jugement porte sur les séries de données. Les tableaux de bord
    en données en direct ne pouvaient jamais réussir hors de l'application → le contrat s'était
    trompé : `DOD-9` révisé et daté, la consigne dit à l'agent de ne pas s'acharner sur ces erreurs ;
  - passe 2 : une légende de couleur Plot était jugée « graphique vide » → confirmé sur un vrai rendu
    Plot 0.6, corrigé ;
  - passe 3 : rien à signaler.
- **Premier commit du contrat** : 2026-09-18 16:37 (`3878ff1`) · **premier commit de code** :
  2026-09-18 16:50 (`b307e28`).

> Règle de lecture pour le pair : du code daté **avant** le contrat, on ne signe pas — on va
> d'abord chercher un avis technique.

## Ce que cette PR change dans l'outillage

Rien dans l'outillage du parcours. **Zone critique** : le `Dockerfile` installe Chromium (headless
shell) dans l'image de production, qui s'alourdit d'autant — le consentement d'un owner est requis.
Ce changement touche une zone critique et nécessite une relecture humaine.

Validation du contrat : faite **par délégation** (l'agent jouait le demandeur), avec les cinq
décisions à leur valeur par défaut — à confirmer ou contester ici.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
