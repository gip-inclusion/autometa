# Lire les comptes Brevo

## Ce que je veux

Le tableau « Centre des emails » montre tous les emails envoyés aux professionnels. Aujourd'hui, il relit une copie que n8n fait chaque nuit dans une base Notion, avec jusqu'à un jour de retard. Je veux qu'Autometa lise directement les trois comptes Brevo de l'équipe (marketing, Emplois, DORA), sans jamais lire les contacts.

## Ce qui devra marcher

DOD-1 — Un tableau de bord liste les modèles d'email d'un compte Brevo, avec leur nom, leur objet et leur état, actif ou non.

DOD-2 — Un tableau de bord liste les campagnes d'un compte, les plus récentes d'abord, avec leurs envoyés, délivrés, ouvreurs, cliqueurs et désinscrits.

DOD-3 — Un tableau de bord compte les envois par modèle sur les 30 derniers jours, et sur 90 jours au plus. Pour un compte qui envoie 30 000 emails par mois, la réponse arrive en moins de 10 secondes.

DOD-4 — Rien de ce qui sort de Brevo ne contient une adresse email. Un email envoyé sans modèle est compté par son objet, et un objet vu moins de cinq fois ne sort pas : il est compté avec les autres sur une seule ligne.

DOD-5 — Une lecture que le connecteur ne prévoit pas (contacts, listes, une autre route) est refusée avant tout appel à Brevo, avec un message qui dit ce qui est permis.

DOD-6 — L'agent lit les mêmes informations par une skill, et la page « Sources de données » montre chaque compte et dit s'il répond.

## Sources lues

- `CONTRIBUTING.md` et `docs/paved-road/l0-definition-of-done.md` : format de ce fichier.
- `docs/interactive-dashboards.md` : la façade et `/api/query`, par où un tableau lit une source.
- `config/sources.yaml` : les sources à plusieurs instances, comme Metabase et Matomo.
- `.claude/rules/review.md` : une PR par changement logique, aucune donnée personnelle dans le dépôt public.

## Questions ouvertes

1. Le seuil de cinq envois pour garder un objet sans modèle. Défaut retenu : cinq. Sur le compte DORA, il ramène 1 009 lignes à 126 et masque les objets qui portent le nom d'une structure.
2. Chaque compte a sa propre clé, dédiée à Autometa. Défaut retenu : trois variables d'environnement, déclarées comme instances dans `config/sources.yaml`.

## Validation

Validé par Mehdi Aïda le 2026-11-22.
