---
name: brevo
description: Lire les comptes Brevo de l'équipe (marketing, Emplois, DORA) — modèles d'email, campagnes et leurs statistiques, nombre d'envois par modèle. Lecture seule, sans aucun contact. À utiliser dès qu'une demande porte sur les emails envoyés par l'équipe ou par les produits via Brevo.
---

# Brevo — modèles, campagnes et volumes d'envoi

Accès **lecture seule** aux comptes Brevo de l'équipe. Chaque compte a sa clé :

- `marketing` : les campagnes et les parcours de l'équipe growth ;
- `emplois` : les emails envoyés par La plateforme de l'inclusion ;
- `dora` : les emails envoyés par DORA.

`--instances` liste les comptes configurés dans cet environnement.

## Ce que la skill ne lit pas

Les contacts et les listes ne sont jamais lus. Les événements d'envoi portent l'adresse du destinataire : le client les compte par modèle et ne rend que les totaux. Une question sur une personne (« X a-t-il reçu tel email ? ») ne se traite pas ici. Dans les noms, objets, aperçus, tags et le contenu HTML, chaque adresse email est remplacée par « [adresse masquée] ».

## Commandes

```bash
# Modèles d'email du compte (nom, objet, actif, tag, dates) ; --content ajoute le HTML
python skills/brevo/scripts/query.py --instance emplois --templates [--content]

# Campagnes, les plus récentes d'abord, avec envoyés, délivrés, ouvreurs, cliqueurs, désinscrits
python skills/brevo/scripts/query.py --instance marketing --campaigns [--status sent] [--content]

# Nombre d'envois par modèle sur 30 jours (90 au plus), avec la date du dernier envoi
python skills/brevo/scripts/query.py --instance emplois --sends --days 30
```

## Lire les chiffres

- Un modèle `isActive: false` peut encore avoir des envois : c'est l'automatisation qui l'utilise qui décide, pas le modèle.
- `--sends` compte les demandes d'envoi. Une ligne de modèle donne son `templateId`, son nombre d'envois et sa dernière date ; son objet se lit par `--templates`.
- Un email envoyé par un produit sans passer par un modèle Brevo a `templateId: null` : il est compté par objet, une ligne par objet distinct. Les objets vus moins de cinq fois, ou qui contiennent une adresse, sont personnalisés (nom d'une structure, parfois d'une personne) : ils sont regroupés dans une seule ligne sans objet, dont `subjects` donne le nombre d'objets distincts.
- Les taux d'ouverture sont gonflés par les ouvertures automatiques des messageries (Apple notamment) ; les clics sont plus fiables.
- Si `truncated` vaut `true`, la fenêtre dépasse 100 000 événements : réduire `--days`.

## Dans un tableau de bord

- Dans `cron.py` : `query_brevo("emplois", "sends_by_template", {"days": 30})` (façade `lib.dashboard_api`).
- En direct depuis la page : `/api/query` avec `{"source": "brevo", "instance": "emplois", "method": "templates", "params": {}}`. Ce mode rend le tableau non publiable (voir `docs/interactive-dashboards.md`).

Méthodes : `templates` (`with_content`), `campaigns` (`status`, `with_content`), `sends_by_template` (`days`).
