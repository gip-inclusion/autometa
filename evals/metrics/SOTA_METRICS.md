# SOTA Metrics — Revue et recommandations

Revue des métriques d'évaluation de l'état de l'art applicables à autometa : un agent conversationnel qui fait du tool-use (SQL, API Matomo/Metabase, lecture de fichiers), génère des analyses en français, et produit des artefacts (dashboards, CSV, rapports).

## 1. Exact / Token / Fuzzy Match

### 1a. Exact Match

- **Lib** : built-in (`==`) ou `evaluate` (`exact_match`)
- **Domaine** : QA extractive, classification, SQL exact
- **Forces** : déterministe, sans ambiguïté, rapide
- **Faiblesses autometa** : quasi inutilisable seule — les réponses agent sont libres (formatage variable, synonymes, ordre des colonnes SQL différent). Utilisable uniquement pour des sous-tâches très contraintes (nom de site, ID Matomo, nom d'une skill)
- **Coût** : CPU, O(n)

```python
def exact_match(prediction: str, reference: str) -> float:
    """Returns 1.0 if exact match, 0.0 otherwise."""
    ...
```

### 1b. Token-level F1 (SQuAD-style)

- **Lib** : `evaluate` (`squad`) ou implémentation maison
- **Domaine** : QA extractive
- **Forces** : tolère les variations d'ordre et les mots superflus
- **Faiblesses autometa** : problématique pour le français (tokenization, accents, articles). Ne capture pas la sémantique — "le taux a augmenté de 5%" et "hausse de 5 points" ont un F1 bas malgré un sens similaire
- **Coût** : CPU, O(n)

```python
def token_f1(prediction: str, reference: str, lang: str = "fr") -> dict[str, float]:
    """Returns {'precision': float, 'recall': float, 'f1': float}."""
    ...
```

### 1c. Levenshtein normalisé

- **Lib** : `python-Levenshtein` ou `rapidfuzz`
- **Domaine** : fuzzy matching, typos, variations mineures
- **Forces** : capte les reformulations légères, utile pour comparer du SQL quasi-identique
- **Faiblesses autometa** : distance d'édition entre deux SQL sémantiquement équivalents peut être élevée (`WHERE a = 1 AND b = 2` vs `WHERE b = 2 AND a = 1`)
- **Coût** : CPU, O(n*m)

```python
def normalized_levenshtein(prediction: str, reference: str) -> float:
    """Returns 1.0 - (edit_distance / max(len(pred), len(ref)))."""
    ...
```

**Recommandation** : Token F1 comme baseline bon marché. Exact match uniquement pour les champs structurés (site ID, skill name).

---

## 2. N-gram Overlap

### 2a. BLEU (sacrebleu)

- **Lib** : `sacrebleu` (canonical) — `pip install sacrebleu`
- **Domaine** : traduction, text-gen
- **Forces** : standard, reproductible (sacrebleu version pinning), multi-référence natif
- **Faiblesses autometa** : conçu pour la traduction — pénalise les réponses longues (brevity penalty) ou les reformulations. Un agent qui explique en 3 paragraphes ce que le gold dit en 1 aura un BLEU faible même si correct. Inadapté au SQL (l'ordre des tokens n'est pas significatif)
- **Coût** : CPU, O(n)

```python
def compute_bleu(predictions: list[str], references: list[list[str]]) -> dict[str, float]:
    """Returns {'bleu': float, 'brevity_penalty': float, 'precisions': list[float]}."""
    ...
```

### 2b. ROUGE-L (rouge-score)

- **Lib** : `rouge-score` — `pip install rouge-score`
- **Domaine** : résumé, text-gen
- **Forces** : la variante ROUGE-L (longest common subsequence) est plus tolérante aux réordonnances que BLEU. Bon proxy pour "l'information clé est-elle présente"
- **Faiblesses autometa** : même problème que BLEU — les réponses d'agent sont très variables en longueur/style. ROUGE-L favorise les réponses verbeuses qui reprennent les termes du gold
- **Coût** : CPU, O(n*m)

```python
def compute_rouge_l(prediction: str, reference: str) -> dict[str, float]:
    """Returns {'precision': float, 'recall': float, 'fmeasure': float}."""
    ...
```

**Recommandation** : ROUGE-L recall comme filtre rapide (si < 0.3, la réponse rate probablement l'information clé). Pas de décision finale basée sur BLEU/ROUGE seuls.

---

## 3. Embedding-based

### 3a. BERTScore

- **Lib** : `bert-score` — `pip install bert-score`
- **Modèle recommandé** : `camembert-base` (français) ou `microsoft/deberta-xlarge-mnli` (anglais)
- **Domaine** : text-gen, résumé, paraphrase
- **Forces** : capture la similarité sémantique — "le nombre de candidatures a baissé" ≈ "on observe une diminution des candidatures". Multilingue avec le bon modèle
- **Faiblesses autometa** : ne distingue pas les erreurs factuelles subtiles ("augmenté de 5%" vs "diminué de 5%" ont des embeddings proches). Nécessite GPU pour être rapide. Ne comprend pas la structure SQL
- **Coût** : GPU recommandé, ~0.5s/pair avec `camembert-base` sur CPU

```python
def compute_bertscore(
    predictions: list[str],
    references: list[str],
    model: str = "camembert-base",
) -> dict[str, list[float]]:
    """Returns {'precision': [...], 'recall': [...], 'f1': [...]}."""
    ...
```

### 3b. MoverScore

- **Lib** : `moverscore` — implémentation research (pas de package pip stable)
- **Domaine** : text-gen avancé
- **Forces** : utilise le transport optimal pour aligner les tokens — plus robuste que BERTScore pour les permutations
- **Faiblesses autometa** : implémentation fragile, peu maintenue, pas de modèle français officiel. L'avantage marginal sur BERTScore ne justifie pas le coût d'intégration
- **Coût** : GPU, plus lent que BERTScore

**Non recommandé** pour autometa — BERTScore suffit.

### 3c. BLEURT

- **Lib** : `bleurt` (Google) — `pip install bleurt @ https://...`
- **Domaine** : évaluation de traduction/generation apprise
- **Forces** : corrélation humaine supérieure à BLEU/ROUGE/BERTScore sur WMT
- **Faiblesses autometa** : entraîné sur l'anglais uniquement, pas de modèle français. Taille modèle ~1 GB. Ne justifie pas l'investissement vu le multilinguisme requis
- **Coût** : GPU, modèle 1 GB

**Non recommandé** — préférer BERTScore avec `camembert-base`.

**Recommandation** : BERTScore F1 avec `camembert-base` comme métrique sémantique principale. Seuil de confiance à calibrer sur le corpus annoté.

---

## 4. LLM-as-Judge

### 4a. G-Eval (prompt-based)

- **Lib** : custom prompt — pas de package standard
- **Domaine** : toute tâche générative
- **Forces** : la plus flexible et la plus corrélée avec le jugement humain. Peut évaluer des dimensions spécifiques (exactitude factuelle, pertinence, complétude, style). Multi-référence naturellement. Supporte les réponses longues et structurées
- **Faiblesses autometa** :
  - **Biais positionnel** : le juge favorise la première ou la dernière réponse dans les comparaisons A/B
  - **Auto-favoritisme** : Claude jugera les réponses de Claude plus favorablement
  - **Coût** : chaque évaluation coûte ~1-2K tokens d'input
  - **Reproductibilité** : variance intra-juge (même prompt, même input → scores différents). Mitigation : 3-5 runs avec moyenne
  - **Intra-rater agreement** : ~80-85% pour des jugements binaires, plus faible pour les scores continus

```python
def llm_judge(
    prediction: str,
    reference: str | None,
    context: str,
    axes: list[str],
    model: str = "claude-sonnet-4-6",
    n_runs: int = 3,
) -> dict[str, float]:
    """
    Axes: 'correctness', 'helpfulness', 'relevance', 'completeness', 'style'.
    Returns {axis: mean_score_1_to_5} averaged over n_runs.
    """
    ...
```

### Axes d'évaluation recommandés pour autometa

| Axe | Description | Poids suggéré |
|-----|-------------|---------------|
| **Correctness** | Les faits/chiffres/SQL sont-ils exacts ? | 0.35 |
| **Completeness** | Toutes les dimensions demandées sont-elles couvertes ? | 0.25 |
| **Relevance** | La réponse répond-elle à la question posée ? | 0.20 |
| **Helpfulness** | La réponse est-elle actionnable pour un analyste ? | 0.10 |
| **Style** | Français correct, pas de jargon LLM, formatage propre ? | 0.10 |

### Mitigations des biais

1. **Biais positionnel** : évaluer pred vs ref ET ref vs pred, moyenner
2. **Auto-favoritisme** : acceptable pour maintenant avec Sonnet comme juge — revisiter si les scores semblent biaisés
3. **Variance** : 3 runs minimum, rapporter mean + std
4. **Calibration** : inclure 10-20 paires annotées humainement comme anchor set

**Recommandation** : LLM-as-judge est la **métrique primaire** pour autometa. C'est la seule qui peut évaluer des réponses longues, multi-paragraphes, contenant du SQL + de l'analyse textuelle + des recommandations.

---

## 5. Multi-référence

- **Principe** : pour une même question, plusieurs réponses "correctes" sont possibles (SQL différents qui retournent le même résultat, formulations alternatives de l'analyse)
- **Implémentation** : le gold standard contient un champ `acceptable_alternatives` (cf. GOLD_FORMAT.md)
- **Métriques compatibles** : BLEU (natif), LLM-judge (instructions "acceptable if matches any of…")

```python
def multi_reference_score(
    prediction: str,
    references: list[str],
    metric_fn: callable,
) -> float:
    """Returns max(metric_fn(prediction, ref) for ref in references)."""
    ...
```

---

## 6. Pass@k (code/SQL)

- **Lib** : implémentation custom (formule HumanEval)
- **Domaine** : génération de code, SQL
- **Principe** : générer k échantillons, compter combien passent le test → `pass@k = 1 - C(n-c, k) / C(n, k)` où c = nombre de samples corrects
- **Forces autometa** : directement applicable à la génération SQL — l'agent génère un SQL, on l'exécute, on compare le résultat au gold. Capture la variabilité du modèle
- **Faiblesses** : nécessite k invocations (coûteux en tokens). Pour autometa, k=1 (pass@1) est le cas réaliste — l'utilisateur n'a qu'une seule réponse
- **Coût** : k × coût d'une génération

```python
def pass_at_k(
    n_samples: int,
    n_correct: int,
    k: int = 1,
) -> float:
    """Unbiased estimator of pass@k."""
    ...
```

**Recommandation** : pass@1 pour le SQL (l'agent ne génère qu'une réponse). Intégré dans la métrique SQL app-context (cf. APP_METRICS.md).

---

## Synthèse — Top 3 métriques SOTA recommandées

| Priorité | Métrique | Usage principal | Coût |
|----------|----------|-----------------|------|
| 1 | **LLM-as-Judge** (Sonnet, multi-axes) | Qualité globale des réponses agent | $$$ (tokens) |
| 2 | **SQL Execution Match** (pass@1) | Exactitude des requêtes SQL | $ (DB query) |
| 3 | **ROUGE-L recall** | Filtre rapide de couverture informationnelle | $ (CPU) |

Les métriques d'overlap textuel (BLEU, Token F1, Levenshtein) et d'embedding (BERTScore) sont **écartées** : la valeur de l'agent est dans ses actions (SQL, tool-use, skill routing), pas dans la formulation de ses réponses. LLM-as-judge couvre la qualité textuelle de manière plus fiable.

### Métriques écartées et pourquoi

| Métrique | Raison |
|----------|--------|
| BERTScore | La qualité textuelle est déjà couverte par LLM-judge — pas besoin d'une métrique d'embedding séparée (+ dépendance GPU) |
| BLEU | Brevity penalty inadapté aux réponses agent longues |
| MoverScore | Implémentation fragile, gain marginal |
| BLEURT | Anglais uniquement |
| Token F1 | Trop superficiel — n-gram overlap ne capture pas la sémantique |
| Exact Match seul | Trop strict pour des réponses libres |
| Levenshtein | Trop sensible aux reformulations sémantiquement équivalentes |
