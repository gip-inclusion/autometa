# Phase 1 — Contrat du snippet rendu

**Feature** : Intégration Matomo Tag Manager sur Autometa
**Date** : 2026-04-13

Cette fonctionnalité n'expose **aucune API HTTP, CLI ou interne** nouvelle. Le seul « contrat » observable est la sortie HTML produite par le template `web/templates/base.html`. Ce document fige cette sortie pour servir de base aux tests.

## Variables Jinja exposées

Définies dans `web/deps.py`, accessibles depuis tous les templates :

| Variable | Type | Source | Vide signifie |
|---|---|---|---|
| `matomo_tag_manager_container_id` | `str` | `web.config.MATOMO_TAG_MANAGER_CONTAINER_ID` | Pas de conteneur configuré → snippet non rendu |
| `matomo_url` | `str` | `web.config.MATOMO_URL` (défaut : `https://matomo.inclusion.beta.gouv.fr`) | Toujours défini ; sert à construire l'URL du conteneur |

## Sortie HTML — cas « ID configuré »

Quand `matomo_tag_manager_container_id` est non vide, le `<head>` de `base.html` contient le snippet officiel Matomo Tag Manager (forme exacte fournie par MTM, équivalente à) :

```html
<!-- Matomo Tag Manager -->
<script>
var _mtm = window._mtm = window._mtm || [];
_mtm.push({'mtm.startTime': (new Date().getTime()), 'event': 'mtm.Start'});
(function() {
  var d = document, g = d.createElement('script'), s = d.getElementsByTagName('script')[0];
  g.async = true;
  g.src = '{{ matomo_url }}/js/container_{{ matomo_tag_manager_container_id }}.js';
  s.parentNode.insertBefore(g, s);
})();
</script>
<!-- End Matomo Tag Manager -->
```

Garanties testables :

1. La balise `<script>` du snippet est présente exactement **une seule fois** dans la page.
2. L'attribut `g.async = true` est présent (chargement non bloquant — EF-004).
3. L'URL injectée est de la forme `{matomo_url}/js/container_{id}.js` avec les valeurs venant des variables Jinja (pas d'interpolation en dur).
4. Le snippet est rendu **dans `<head>`**, **avant** `{% block head %}{% endblock %}`.

## Sortie HTML — cas « ID absent ou vide »

Quand `matomo_tag_manager_container_id` vaut `""` ou n'est pas défini :

- **Aucune** balise `<script>` MTM n'est présente dans le HTML rendu.
- **Aucun** marqueur résiduel (commentaire « Matomo Tag Manager », initialisation `window._mtm`, etc.) n'est présent.

Ce comportement no-op est ce qui couvre les environnements non-prod par défaut (cf. clarification Q1 de la spec, EF-006).

## Périmètre

Ce contrat s'applique à **toutes les pages applicatives** d'Autometa qui étendent `web/templates/base.html` (cf. EF-001). Les apps interactives sous `/interactive/` sont hors périmètre — elles ne sont pas censées rendre ce snippet.
