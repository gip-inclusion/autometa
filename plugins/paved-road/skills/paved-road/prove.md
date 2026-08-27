# Prove — une preuve par critère

But : pour chaque `DOD-N`, une commande réelle, son code de sortie, et le lien entre cette preuve
et l'état exact du code qu'elle a prouvé.

Le demandeur verra le résultat dans la description de PR : démontré, non démontré, périmé.

## Dans l'ordre

Pour chaque critère :

```
make paved-road-advance DOD=DOD-1 CMD='uv run --frozen pytest tests/test_rapports.py -k dod_1'
```

`advance` exécute la commande, écrit `paved-road/<slug>/attestations/DOD-1.md` — la commande, son
code de sortie, la sortie tronquée, les empreintes d'arbre de `web`, `lib`, `scripts`, `skills`,
`alembic`, `tests`, et le verdict. Il refuse si un chemin prouvé a des modifications non
committées : on ne prouve que du code enregistré.

## Quelle preuve pour quel critère

| Le critère parle de… | Preuve admise | Rejouée en CI ? |
|---|---|---|
| un comportement du code (`web/`, `lib/`) | un test unitaire ciblé : `uv run --frozen pytest tests/… -k dod_N` | oui |
| un parcours dans le navigateur | un `test_dod_N` sous `browser/`, joué par le workflow E2E. Verdict `démontré (E2E)`, **non rejoué** par le contrôle requis — il échouerait faute de navigateur et d'application servie | non |
| une migration | `alembic check`, plus la migration jouée sur une base fraîche | oui |
| un `SKILL.md`, un fichier `knowledge/` | frontmatter valide, chemins cités existants. La preuve comportementale viendra avec les evals | oui |
| un chiffre : volumétrie, durée | une mesure en nightly, hors chemin bloquant. Verdict `démontré (nightly)`, non rejoué. **Le contrat doit l'annoncer d'avance** | non |

## Ce qu'une commande de preuve ne peut pas être

- `true`, `echo`, ou toute commande décorative ;
- `pytest --version`, `pytest --collect-only`, `--co` : collecter n'est pas exécuter ;
- un test sans rapport avec le critère. La commande doit **exécuter** au moins un test dont
  l'identifiant contient `dod_N`.

Ces règles ferment la preuve vide. Elles ne jugent pas si le corps du test démontre vraiment le
bon comportement — aucun programme ne sait le faire. C'est au pair de lire les critères, et à la
lentille d'avoir comparé le code au contrat à l'étape précédente.

## Si un critère ne peut pas être prouvé

Ne le maquille pas. Laisse-le « non démontré », et écris pourquoi dans la description de PR.
Un critère non démontré et annoncé se discute ; un critère faussement démontré se découvre en
production.

Si le critère lui-même est infaisable — le contrat s'est trompé — c'est une révision : dis-le au
demandeur, révise la ligne concernée en la datant (`Révision AAAA-MM-JJ`), et reprends.

## Quand tout est démontré

Passe à `pr.md`.

## Si une preuve devient périmée

Elle le devient dès qu'un des chemins empreintés change — y compris quand `main` avance sous toi
et que tu rebases. Le contrôle « Ce qui devait marcher » vire au rouge et le dit : c'est une panne
réparable, tu reprends les preuves concernées. Si l'interface a changé, le smoke est à refaire
aussi, et il demande une présence humaine : préviens le demandeur au lieu de le découvrir avec lui.
