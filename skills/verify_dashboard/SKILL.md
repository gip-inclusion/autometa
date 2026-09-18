---
name: verify_dashboard
description: Vérifier la qualité visuelle d'un tableau de bord (TDB) en le rendant dans un navigateur sans écran — erreurs JavaScript, fichiers non chargés, graphiques vides ou manquants, valeurs NaN/undefined, mise en page cassée. MUST be invoked as the last step after writing or modifying a dashboard's files, before giving its URL to the user.
---

# Verify Dashboard Skill

Affiche le TDB comme le verrait un utilisateur et rend un verdict **réussi / échoué** avec la liste des
problèmes. Le skill sert lui-même le dossier du TDB : aucune application démarrée n'est nécessaire.

## Quand le lancer

Après `create_dashboard` ou `update_dashboard`, **une fois les fichiers du TDB écrits** — et, s'il a un
`cron.py`, après l'avoir lancé une première fois pour générer `data.json`. Une modification qui ne
touche que les métadonnées (titre, tags, archivage) ne se vérifie pas.

## Usage

```bash
.venv/bin/python skills/verify_dashboard/scripts/verify_dashboard.py mon-tdb --expect-charts 3
```

| Argument | Description |
|---|---|
| `target` | Slug du TDB (dossier `data/interactive/{slug}/`) ou chemin d'un dossier |
| `--expect-charts` | Nombre de graphiques que le TDB doit afficher. Le passer dès que le TDB en a ; sans lui, aucun minimum n'est exigé |

Sortie sur stdout (JSON) :

```json
{
  "target": "mon-tdb",
  "passed": false,
  "issues": [
    {"severity": "error", "message": "graphique canvas #evolution affiché sans aucun tracé"},
    {"severity": "warning", "message": "données en direct non vérifiées : http://127.0.0.1:41235/api/query"}
  ]
}
```

## Ce qui fait échouer le verdict

- une erreur JavaScript ou une erreur écrite dans la console ;
- un fichier du TDB (données, script, feuille de style, CDN…) qui ne se charge pas ;
- un graphique visible sans aucun tracé, ou moins de graphiques que `--expect-charts` ;
- `NaN`, `undefined`, `null` ou `[object Object]` affichés dans la page ;
- un débordement horizontal sur un écran de 1280 px, ou une page sans texte ;
- le bloc `#error` affiché, ou `#loading` encore visible ;
- une page qui n'a pas fini de charger en 30 s ;
- un dossier sans `index.html`.

Ne font **pas** échouer : le tag manager Matomo (bloqué pendant la vérification, pour ne pas compter
de fausse visite) et les appels `/api/…` des TDB en données live, impossibles hors de l'application —
ils sortent en avertissement « données en direct non vérifiées ».

## Conduite à tenir

- **Réussi** (code `0`) : donner le lien à l'utilisateur.
- **Échoué** (code `1`) : corriger chaque problème de sévérité `error`, puis relancer — **trois
  tentatives au plus**. Si des problèmes restent, donner le lien **en les listant** à l'utilisateur ;
  ne jamais présenter le TDB comme vérifié.
