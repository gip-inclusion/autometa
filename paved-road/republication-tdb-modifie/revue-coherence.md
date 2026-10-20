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
