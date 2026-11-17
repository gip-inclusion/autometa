# Bibliothèques de graphiques des tests `browser/`

Copies non modifiées des bibliothèques que `docs/interactive-dashboards.md` prescrit aux TDB, servies par
`page.route` à la place du CDN dans `browser/test_verify_dashboard.py`.

Pourquoi les vendorer : `verify_dashboard` juge un graphique sur ce que la bibliothèque a réellement calculé ou
dessiné. Un faux `window.Chart` ou un svg reproduit à la main ne montre que ce que le test suppose ; c'est ainsi que
des barres horizontales tracées passaient pour vides (review de #230). Hors réseau, les tests restent déterministes
et ne dépendent pas de la disponibilité du CDN.

Elles ne sont chargées que par les tests, jamais par l'application ni par un TDB.

| Fichier | Version | Source | sha256 |
|---|---|---|---|
| `chart.umd.js` | Chart.js 4.5.1 | `https://cdn.jsdelivr.net/npm/chart.js@4.5.1/dist/chart.umd.js` | `ecc3cd1eeb8c34d2178e3f59fd63ec5a3d84358c11730af0b9958dc886d7652a` |
| `d3.min.js` | D3 7.9.0 | `https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js` | `f2094bbf6141b359722c4fe454eb6c4b0f0e42cc10cc7af921fc158fceb86539` |

Mise à jour : retélécharger depuis la même URL avec la nouvelle version, mettre à jour ce tableau, rejouer
`pytest browser`.
