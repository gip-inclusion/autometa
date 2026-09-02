# L5 — Adversarial Review : `paved-road:design-coherence`

Origine et justifications : `docs/plans/2026-08-22-paved-road-workflow.md`, section « L5 —
Adversarial Review ».

## Une seule lentille, et pourquoi

`paved-road:design-coherence` pose la seule question qu'aucun autre niveau ne pose : le code fait-il ce que la
definition of done dit, ni plus ni moins ? `ruff`, `bandit`, `gitleaks`, le gate de couverture et les
tests Playwright constatent la forme ; aucun ne connaît l'intention. Sans L0 elle n'aurait d'ailleurs
aucun référentiel et se réduirait à du commentaire de style — c'est pourquoi elle démarre ici et pas
plus tôt.

Elle est lancée **dans le flot, par un sous-agent** (`plugins/paved-road/agents/design-coherence.md`), et
appartient aux Adapters : elle améliore le résultat, elle ne garantit rien.

## Warning permanent

Une lentille LLM n'est pas un exécutable reproductible : deux exécutions sur le même diff ne
rendent pas le même texte. Elle ne peut donc pas vivre dans les Guardrails, et **ne devient jamais
bloquante** — ce n'est pas une étape du ratchet, c'est son régime définitif. Un gate dont le verdict
varie sans que le code ait changé n'apprend rien à personne : il apprend à passer outre.

## Ce qui n'est pas ici, et pourquoi

**`auth-audit` en est sortie.** Le ratchet suppose qu'un premier incident soit rattrapable ; une
exposition de données de demandeurs d'emploi ne l'est pas. Un check déterministe la remplace :
`scripts/check_route_auth.py`, avec sa baseline gelée dans `gates.toml`.

**Le catalogue de réserve reste en réserve.** `abstraction-quality`, `surgical-changes`,
`test-quality`, `edge-case-hunter`, `security-auditor`, `legal-compliance`, `dod-test-fidelity`,
`query-cost`, `knowledge-drift` : le design les liste, et elles s'ajoutent **une par une, quand le
friction log les réclame**. Les vingt verifiers d'`akria-pipeline` ne sont pas nés d'un design mais
de vingt incidents ; les copier d'emblée reviendrait à payer leurs cicatrices sans avoir eu leurs
blessures.

Deux besoins souvent cités n'y figureront pas : la conformité aux `.claude/rules/` relève des règles
ruff (L6), la sûreté des migrations de L2 — validation contre des données réelles, pas jugement d'un
modèle. Une lentille LLM qui vérifie ce qu'un `grep` fait mieux est du gaspillage.

## Ajouter la suivante

Une entrée du friction log, pas une intuition. Elle doit nommer l'incident qui l'a réclamée, et la
raison pour laquelle aucun vérificateur déterministe ne pouvait le voir. Sans ces deux lignes, la
lentille reste en réserve.
