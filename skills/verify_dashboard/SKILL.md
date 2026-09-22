---
name: verify_dashboard
description: Vérifier automatiquement la qualité visuelle d'un tableau de bord (TDB) en le rendant dans un navigateur headless — erreurs JS, requêtes en échec, graphiques vides ou absents, mise en page cassée, valeurs NaN/undefined. MUST be invoked as the last step after creating or modifying a dashboard, before giving its URL to the user.
---

# Verify Dashboard Skill

Rend le TDB dans un Chromium headless (Playwright), exactement comme un navigateur d'utilisateur, et
renvoie un verdict structuré. C'est **l'étape finale obligatoire** de toute génération ou modification
de TDB : `create_dashboard` / `update_dashboard` → écriture de `index.html`, `app.js`, `data.json` →
`verify_dashboard` → corrections → `verify_dashboard` → URL donnée à l'utilisateur.

Le skill sert lui-même le dossier du TDB en local (sous `/interactive/{slug}/` et `/common/`, comme
l'application) : aucune application servie ni session n'est nécessaire.

## Usage

```bash
.venv/bin/python skills/verify_dashboard/scripts/verify_dashboard.py mon-tdb --expect-charts 3
```

| Argument | Description |
|---|---|
| `target` | Slug du TDB (dossier `data/interactive/{slug}/`), chemin d'un dossier, ou URL `http(s)://` |
| `--expect-charts` | Nombre minimal de graphiques qui doivent être rendus. **Toujours le passer** : c'est le nombre de graphiques que le TDB est censé afficher |
| `--screenshot` | Chemin de la capture pleine page (défaut `/tmp/verify_dashboard/{slug}.png`) |

Sortie sur stdout (JSON) :

```json
{
  "target": "mon-tdb",
  "url": "http://127.0.0.1:41235/interactive/mon-tdb/",
  "passed": false,
  "charts": 2,
  "screenshot": "/tmp/verify_dashboard/mon-tdb.png",
  "issues": [
    {"check": "chart", "severity": "error", "message": "<canvas #evolution> Chart.js : libellé undefined/NaN"},
    {"check": "request", "severity": "warning", "message": "font https://… → net::ERR_FAILED"}
  ]
}
```

## Ce qui est vérifié

| `check` | Erreur (fait échouer) | Avertissement |
|---|---|---|
| `console`, `pageerror` | Erreur console, exception JS non rattrapée | |
| `request` | Script, style, `data.json`… en échec (HTTP ≥ 400 ou réseau) | Police, image ; appel `/api/…` (non vérifiable hors application servie) |
| `chart` | `<canvas>`/`<svg>` visible de taille nulle ou sans aucun tracé ; moins de graphiques que `--expect-charts` ; Chart.js : libellé `undefined`/`NaN`, série sans aucune valeur | Aucun graphique détecté |
| `layout` | Débordement horizontal (viewport 1280 px) ; page sans texte | `#generated-at` non renseigné |
| `error_text` | `undefined`, `NaN`, `[object Object]`, traceback visibles ; bloc `#error`/`.error`/`[role=alert]` affiché | |

Les graphiques masqués (onglet inactif) et les pictogrammes SVG ne sont pas comptés. Le tag manager
Matomo est bloqué pendant l'audit : il ne compte pas de fausse visite.

## Codes de retour et conduite à tenir

- `0` — verdict positif. Regarder quand même les avertissements et la capture d'écran (outil `Read`
  sur le `.png`) : un graphique peut être tracé et pourtant illisible.
- `1` — verdict négatif. **Corriger chaque issue `error` puis relancer**, jusqu'au verdict positif.
  Si une erreur ne peut pas être corrigée, livrer quand même le TDB mais **le signaler explicitement
  à l'utilisateur** avec la liste des issues restantes. Le contrôle informe, il ne bloque ni la
  création ni l'enregistrement du TDB.
- `2` — audit impossible (TDB sans `index.html`, navigateur absent). Le dire à l'utilisateur ; ne pas
  présenter le TDB comme vérifié.

## Limites

- Un TDB en mode `/api/query` (live) ou `dashboard_storage` n'a pas ses données hors application
  servie : ses requêtes `/api/…` ressortent en avertissement et ses graphiques peuvent être vides.
  Pour ce cas, passer l'URL d'une instance locale (`make dev`) en `target`.
- D3 / Observable Plot sont jugés sur la présence de tracés SVG, Chart.js en plus sur ses données :
  la justesse des chiffres reste à vérifier par l'agent.
- Capture d'écran : fichier de travail sous `/tmp`, jamais à committer ni à déposer dans
  `data/interactive/` (données potentiellement personnelles).
