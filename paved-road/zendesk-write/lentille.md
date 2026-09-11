# Lentille design-coherence — 2026-09-11

Aucun bloqueur. Dix-sept critères rattachés à du code identifiable. Six remarques, et ce qui en a été fait :

- **DOD-11, rappel du mode regex nulle part rendu** — corrigé : l'en-tête de `diff.md` liste les paramètres de la proposition (motif, remplacement, regex, balisage), et le déroulé de relecture du skill demande d'énoncer le mode.
- **DOD-5 et DOD-6, articles sautés identifiés par id et non nommés** — corrigé : les entrées `skipped` et `errors` portent le titre de l'article.
- **Excès, lectures sans critère** (`search_articles`, `section_id`, `locale`, `user_segment_id`, `list_changesets`) — conservé. `search_articles` a été discuté avec le demandeur (recherche par sujet, distincte du filtrage exact) ; `list_changesets` sert à retrouver une proposition en attente d'une conversation précédente ; les autres sont des paramètres de l'API Zendesk exposés tels quels, sans logique propre.
- **Excès, `plan(**notes)` et repli `{}` sur réponse sans corps** — conservé. Le repli sert au `DELETE` d'un article (204 sans corps), utilisé par le test d'aller-retour sur le bac à sable.
- **Excès, fusion du skill `zendesk_query` dans `zendesk`** — conservé, décidé avec le demandeur : le skill est le support de `DOD-3` et `DOD-8`, et deux fiches pour un seul client auraient contredit l'une l'autre.
- **Relecture systématique après écriture, trois appels par article** — conservé, c'est ce qui rend la garde de `revert` exacte (`DOD-6`).
