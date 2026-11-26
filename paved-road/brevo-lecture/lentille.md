# Lentille design-coherence — 2026-11-22

Deux passes. Deux bloqueurs à la première, corrigés ; aucun à la seconde.

**BLOQUEUR (passe 1) — DOD-4, « aucune adresse » réalisé par le seul retrait du champ `email`** — corrigé.
- Une ligne de modèle ne rend plus que `templateId`, `count` et `lastDate` : l'objet rendu chez un destinataire peut porter une donnée qui le concerne, et l'objet du modèle se lit par `templates`.
- Un objet sans modèle qui contient une adresse rejoint la ligne regroupée, même vu cinq fois ou plus.
- Les adresses sont remplacées par « [adresse masquée] » dans le HTML, les noms, les objets, les aperçus et les tags.
- `report`, qui rendait la réponse de Brevo sans liste blanche, est retiré.
- Relevé réel sur les trois comptes : aucun « @ » dans les envois ; dans le HTML des 198 modèles, les « @ » restants sont des règles CSS, des URL de polices, une chaîne YouTube et un pseudonyme.

**BLOQUEUR (passe 1) — DOD-5, refus de paramètre sans la liste de ce qui est permis** — corrigé. Le refus liste les paramètres permis, `/api/query` sans méthode liste les méthodes, et `days` doit être un entier.

Remarques, et ce qui en a été fait :

- **DOD-3, borne des 10 s** — la phrase du critère porte sur 30 000 envois par mois, donc sur la fenêtre de 30 jours. Mesure réelle : 4,1 s pour 30 069 envois sur le compte le plus chargé.
- **DOD-2, statistiques des campagnes anciennes** — vérifié : aucune des 85 campagnes envoyées il y a plus de six mois (la plus ancienne en juillet 2023) n'a de statistiques vides.
- **Excès** — `event` et `report` retirés. `with_content` et les champs de campagne (`listIds`, `tag`, dates) sont gardés : le Centre des emails, cité dans « Ce que je veux », affiche le texte des emails et place chaque campagne.
- **Aucun tableau du diff ne lit encore Brevo** — conservé : le Centre des emails passera sur ce connecteur une fois la PR en production.
- **`_pages` tronque les listes au-delà de 20 pages sans le dire** — conservé : 2 000 campagnes ou 20 000 modèles, quand le compte le plus fourni en a 229 et 87.
- **Ligne sans modèle et sans objet de même forme que la ligne regroupée** — conservé, sans effet sur les adresses ; seule la clé `subjects` les distingue.
- **Motif d'adresse simple** (`a%40b.fr`, `&#64;` non reconnus) — conservé : ces formes sont absentes des trois comptes.
