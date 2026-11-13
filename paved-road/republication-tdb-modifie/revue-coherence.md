# Revue de cohérence au contrat

Lentille `design-coherence` exécutée sur le diff `origin/main...HEAD`.

Verdict : **Rien à signaler**. Les neuf critères DOD-1 à DOD-9 sont réalisés, chacun rattaché à
du code précis. Aucun excès de périmètre. Aucune infidélité.

## Réponse au paragraphe étiqueté « BLOQUEUR — DOD-4 »

Ce n'en est pas un, et le texte de la lentille le dit lui-même (« cela devrait marcher »).

DOD-4 exige qu'après republication, le rechargement de la page reflète l'état réel du serveur.
`publish()` crée la publication dans un bloc `with get_db() as session:` qui **auto-commit en
sortie de bloc** (`web/db.py:84`, docstring « Auto-commits on success »). La route
`POST /api/dashboards/{slug}/publish` retourne après ce commit ; le `window.location.reload()` du
front relit donc une base déjà à jour, et `drifted_environments(list_publications(slug), updated)`
recalcule le retard sur l'état committé. Comportement déjà couvert par les tests d'intégration de
publication existants (`test_publish_endpoint_creates_publication`).

## Remarques non bloquantes

- **Échec partiel de la boucle de republication** : si staging réussit puis production échoue, le
  front s'arrête au premier échec, signale l'erreur et ne recharge pas ; staging reste republié,
  la suggestion persiste pour production. Cohérent avec DOD-8. Le contrat ne promettait pas
  d'atomicité entre environnements ; non traité volontairement (pas de sur-portée).
- **Double message quand le tableau n'est plus publiable** : l'alerte de retard (sans bouton) et le
  message « Publication indisponible » coexistent. Choix assumé : l'alerte informe du retard, le
  message explique pourquoi on ne peut pas agir. DOD-7 est satisfait (bouton absent + message
  présent).

## Second passage — révision DOD-10 et DOD-11 (alerte dans la conversation)

Lentille relancée sur le diff complet (DOD-1 à DOD-11). Verdict : **rien à signaler** sur la
cohérence au contrat. Les onze critères sont réalisés, tracés, et testés (unit + intégration +
navigateur). Aucun excès de périmètre.

La lentille a soulevé, hors de son champ, une **remarque de sécurité** : la route
`GET /api/conversations/{conv_id}/dashboards` était authentifiée mais ne vérifiait pas la propriété
de la conversation — un tiers pouvait, en devinant un identifiant, lire les titres des tableaux
dérivés d'une conversation d'autrui. Corrigé : la route applique désormais `can_mutate_conversation`
(même règle propriétaire que `POST /messages` et les routes de fichiers) — 404 si la conversation
n'existe pas, 403 si elle ne lui appartient pas. Couvert par deux tests de permission. C'est un
invariant de sécurité, pas un critère du contrat.

## Troisième passage — réponse à la revue #260 (cdarnispro)

La revue a approuvé, mais relevé cinq constats. Chacun est traité.

1. **Bloquant — la détection ne voyait pas les changements de contenu.** Le retard se calculait sur
   `Dashboard.updated_at`, qui ne bouge qu'au rename/tag et jamais à l'édition d'un fichier : un
   tableau modifié par l'assistant ne déclenchait rien, un rename déclenchait une fausse alerte. La
   détection compare désormais le **contenu** : les ETags des fichiers *source* de
   `interactive/{slug}/` contre le snapshot figé `publications/{slug}/{publication_id}/` de la
   publication active de chaque environnement (`snapshot_drifted`, `web/publications.py`). Les
   fichiers générés par le cron (`data.json`, `data/*`) sont exclus, donc rafraîchir ne crée pas de
   retard (DOD-9). Nouvelle fonction `s3.etags_under` (S3 injoignable → `{}`, pas de faux retard).
   Tests : `tests/test_publication_drift.py` (modif de source → retard ; données du cron → pas de
   retard), `tests/test_dashboards_routes.py` pilotés par contenu via `_set_drift`.

2. **Important — l'alerte suivait la conversation de création.** Un tableau créé ailleurs puis
   modifié dans une autre conversation n'alertait pas. `drifted_dashboards_for_conversation` retient
   maintenant, en plus des tableaux créés dans la conversation, ceux dont un fichier
   `data/interactive/{slug}/` a été écrit par un outil Write/Edit pendant la conversation (scan des
   messages `tool_use`). *Écart assumé au choix initial (table persistée + migration)* : la
   modification de contenu passe déjà par les outils d'édition, tracés par conversation dans
   `messages` ; dériver le lien en direct délivre exactement DOD-10 **sans migration ni zone
   critique** (ni `web/models.py`/Alembic, ni `web/runner.py`). Une table persistée reste possible si
   l'on veut la durabilité, mais n'apporte aucune robustesse ici. Tests :
   `tests/test_conversation_dashboards.py` (créé ailleurs + modifié ici → signalé ; non touché ici →
   rien).

3. **À traiter — republier en staging laisse l'ancien lien figé.** Choix retenu : assumer et le
   dire. DOD-4 est reformulé — en staging, republier crée un **nouveau** lien de test, l'ancien reste
   figé sur le contenu déjà partagé (une version de test sert à faire vérifier un état précis). En
   production le lien public est stable et montre le nouveau contenu.

4. **À traiter — la production partait avant le staging.** `drifted_environments` suit désormais
   l'ordre `ENVIRONMENTS` (staging avant production) ; la boucle front republie dans cet ordre et, en
   cas d'échec partiel, nomme les environnements déjà republiés avant de recharger la page. Test
   d'ordre dans `tests/test_publication_drift.py`. La remarque « échec partiel » de la section
   précédente est donc caduque : on commence par la version de test.

5. **Mineur — l'alerte de conversation restait affichée à tort / disparaissait au rechargement.**
   `showRepublishAlert` retire l'alerte existante **avant** le `return` sur liste vide (donc après
   une republication faite ailleurs), et `loadConversation` l'appelle au chargement. Test navigateur
   ajouté (`browser/test_republication_conversation.py`).
