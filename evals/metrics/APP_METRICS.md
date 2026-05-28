# App-Context Metrics — autometa-specific

Métriques d'évaluation spécifiques à autometa, conçues pour capturer ce que les métriques SOTA génériques ne mesurent pas : qualité du SQL, pertinence des chemins d'outils, corrections utilisateur, et signaux de dysfonctionnement agent.

---

## 3a. Qualité des requêtes SQL

L'agent autometa génère du SQL contre plusieurs bases (autometa_tables_db, Metabase instances: stats, datalake, dora, rdvi, data_inclusion). Les requêtes SQL sont le principal vecteur de valeur de l'agent — une requête incorrecte produit une analyse erronée.

### Métriques

#### 1. Syntactic Validity

La requête parse-t-elle correctement ?

- **Lib** : `sqlglot` (recommandé — supporte les dialectes PostgreSQL) ou `sqlparse`
- **Implémentation** : parser le SQL avec `sqlglot.parse(sql, dialect="postgres")` — une exception = échec syntaxique
- **Score** : binaire (0 ou 1)

```python
def sql_syntactic_validity(sql: str, dialect: str = "postgres") -> bool:
    """Returns True if SQL parses without error."""
    ...
```

#### 2. Schema Validity

Les tables et colonnes référencées existent-elles dans le schéma réel ?

- **Source schéma** : `documentation.doc_autometa_tables` dans autometa_tables_db (catalogue centralisé). Pour les instances Metabase, utiliser les `MetabaseCard` synchronisées dans la DB autometa (`web/models.py` lignes 315-346)
- **Implémentation** : extraire les identifiants de tables/colonnes via `sqlglot.parse()` → comparer avec le catalogue
- **Score** : `n_valid_refs / n_total_refs` (ratio de références valides)

```python
def sql_schema_validity(
    sql: str,
    schema_catalog: dict[str, list[str]],
) -> dict[str, float | list[str]]:
    """Returns {'score': float, 'invalid_tables': [...], 'invalid_columns': [...]}."""
    ...
```

#### 3. Execution Success

La requête s'exécute-t-elle sans erreur ?

- **Sandbox** : utiliser `EXPLAIN` (pas d'exécution réelle) ou exécuter dans une transaction rollback-only
- **Implémentation** : via `lib.query.execute_query()` avec un wrapper qui fait `BEGIN; EXPLAIN sql; ROLLBACK;`
- **Score** : binaire (0 ou 1), plus le message d'erreur si échec

```python
def sql_execution_success(
    sql: str,
    source: str,
    instance: str,
) -> dict[str, bool | str]:
    """Returns {'success': bool, 'error': str | None}."""
    ...
```

#### 4. Result Correctness

Le résultat correspond-il au gold standard ?

- **Modes de comparaison** :
  - `set_equal` : les ensembles de lignes sont identiques (ignorer l'ordre sauf si `ORDER BY`)
  - `count_match` : le nombre de lignes correspond
  - `value_match` : les valeurs agrégées (SUM, COUNT, AVG) correspondent à ±epsilon
  - `superset` : le résultat contient au moins toutes les lignes du gold (acceptable si l'agent retourne plus)
- **Score** : binaire pour set_equal/count_match, continu pour value_match

```python
def sql_result_correctness(
    prediction_result: list[dict],
    gold_result: list[dict],
    mode: str = "set_equal",
    epsilon: float = 0.01,
) -> dict[str, float | bool]:
    """Returns {'match': bool, 'score': float, 'details': str}."""
    ...
```

#### 5. Efficiency

Le plan d'exécution est-il raisonnable ?

- **Implémentation** : comparer `EXPLAIN ANALYZE` de la requête agent vs gold
- **Proxies** :
  - Nombre de sequential scans vs index scans
  - Coût estimé total (`rows * width`)
  - Nombre de lignes scannées vs retournées (selectivity)
- **Score** : `gold_cost / prediction_cost` (ratio, >1 = agent moins efficace)

```python
def sql_efficiency(
    prediction_plan: dict,
    gold_plan: dict,
) -> dict[str, float]:
    """Returns {'cost_ratio': float, 'seq_scans': int, 'rows_scanned_ratio': float}."""
    ...
```

#### 6. Style Conformity

Le SQL respecte-t-il les conventions de l'équipe ?

- **Règles** (dérivées de `.claude/rules/sql.md` et `code.md`) :
  - Paramètres nommés (`:param`) — pas de `%s`
  - `text()` wrapper pour le raw SQL
  - snake_case pour les alias
  - Pas d'interpolation de valeurs
- **Implémentation** : regex + AST check via sqlglot
- **Score** : nombre de violations / nombre de règles vérifiées

```python
def sql_style_conformity(sql: str) -> dict[str, float | list[str]]:
    """Returns {'score': float, 'violations': [...]}."""
    ...
```

---

## 3b. Qualité des "proxies"

Une métrique sur les "proxies" — deux interprétations possibles :

### Interprétation A — Reformulations intermédiaires

L'agent reformule la question utilisateur en sous-questions avant de lancer des requêtes. La qualité de cette décomposition conditionne la pertinence des résultats.

**Métrique** : `proxy_coherence` — mesure si les sous-questions couvrent la question initiale sans dérive.

- **Implémentation** : extraire le `thinking` block de l'assistant → identifier les sous-questions formulées → LLM-judge pour évaluer la couverture (chaque aspect de la question initiale est-il adressé ?) et la pertinence (pas de sous-questions hors sujet)
- **Score** : `coverage` (0-1) × `relevance` (0-1)

```python
def proxy_coherence(
    user_question: str,
    agent_thinking: str,
    sub_questions: list[str],
) -> dict[str, float]:
    """Returns {'coverage': float, 'relevance': float, 'coherence': float}."""
    ...
```

**Décision** : interprétation A retenue — on veut mesurer que l'agent ne sélectionne pas une métrique apparentée mais pas exactement celle demandée.

---

## 3c. Nombre de corrections utilisateur

Dans une conversation, compter les messages utilisateur qui corrigent une erreur de l'agent.

### Approche 1 — Heuristique (keywords)

Rapide, déterministe, interprétable.

```python
CORRECTION_KEYWORDS_FR = [
    "non", "pas ça", "pas comme ça", "c'est pas",
    "incorrect", "faux", "erreur", "tu te trompes",
    "essaie autrement", "recommence", "refais",
    "j'ai dit", "je voulais", "ce n'est pas ce que",
    "plutôt", "en fait", "pas exactement",
]

def correction_count_heuristic(
    user_messages: list[str],
) -> dict[str, int | float | list[int]]:
    """
    Returns {
        'n_corrections': int,
        'correction_rate': float,  # n_corrections / len(user_messages)
        'correction_indices': list[int],
    }.
    """
    ...
```

### Approche 2 — LLM Judge

Plus précis, capture les corrections implicites (reformulations sans mots-clés négatifs).

```python
def correction_count_llm(
    conversation: list[dict[str, str]],
    model: str = "claude-sonnet-4-6",
) -> dict[str, int | float | list[dict]]:
    """
    Returns {
        'n_corrections': int,
        'correction_rate': float,
        'corrections': [{'turn': int, 'type': str, 'severity': str}],
    }.
    Type: 'explicit' (user says "non"), 'implicit' (reformulation), 'clarification' (not a correction).
    Severity: 'minor' (formatting/style), 'major' (factual error), 'critical' (wrong data source).
    """
    ...
```

### Approche 3 — Hybride (recommandée)

Heuristique en premier filtre, LLM judge pour confirmer et classifier.

```python
def correction_rate(
    conversation: list[dict[str, str]],
    use_llm: bool = True,
) -> dict[str, int | float]:
    """
    Returns {
        'n_corrections': int,
        'correction_rate': float,
        'n_user_turns': int,
        'first_shot_success': bool,  # True if no corrections at all
    }.
    """
    ...
```

### Lien avec l'existant

Le module `lib/failure_detection.py` détecte déjà les auto-corrections de l'agent (quand l'agent dit "je me suis trompé", "erreur de ma part", etc.). La métrique `correction_count` est complémentaire : elle détecte les corrections **par l'utilisateur**, pas par l'agent.

Combinaison recommandée :
- `agent_self_correction_rate` = `lib.failure_detection.find_failure_marker()` sur les messages assistant
- `user_correction_rate` = `correction_rate()` sur les messages user
- `total_correction_rate` = max(agent, user) — car une auto-correction non corrigée par l'user reste un problème

---

## 3d. Métriques additionnelles identifiées

### 4. Tool-Use Chain Length

Nombre d'appels d'outils avant la première réponse textuelle à l'utilisateur.

- **Motivation** : un agent qui fait 15 tool calls avant de répondre est plus lent (latence perçue) et plus risqué (plus de chances d'erreur). Le corpus montre un ratio moyen de 1.66 assistant turns / user turn, avec certaines sessions à 998 tool calls
- **Score** : `chain_length = n_tool_calls_before_first_text_response`
- **Benchmark** : à calibrer sur le corpus — sessions gold avec chain_length annoté comme "optimal" vs "excessif"

```python
def tool_chain_length(
    assistant_turns: list[dict],
) -> dict[str, int | float]:
    """Returns {'total_tool_calls': int, 'chain_length': int, 'unique_tools': int}."""
    ...
```

### 5. Hallucination Signals

L'agent cite-t-il des ressources inexistantes ?

- **Dashboards inexistants** : l'agent mentionne un dashboard Metabase qui n'existe pas dans l'inventaire synchronisé (`MetabaseCard`, `MetabaseDashboard` dans `web/models.py`)
- **Cartes Metabase fantômes** : référence un `card_id` qui n'existe pas
- **Sites Matomo inconnus** : utilise un `site_id` non listé dans `config/sources.yaml`
- **Colonnes inventées** : référence une colonne non présente dans le schéma (couvert par sql_schema_validity, mais ici on cherche aussi dans le texte libre)
- **API signals manquants** : l'agent prétend avoir exécuté une requête mais aucun signal `[AUTOMETA:API:...]` n'est émis (détectable via `lib/api_signals.py`)

```python
def hallucination_signals(
    conversation: list[dict],
    known_cards: set[int],
    known_sites: dict[int, str],
    known_columns: dict[str, list[str]],
) -> dict[str, int | list[str]]:
    """
    Returns {
        'phantom_cards': [...],
        'phantom_sites': [...],
        'phantom_columns': [...],
        'missing_api_signals': int,
        'total_hallucination_score': float,
    }.
    """
    ...
```

### 6. Skill Routing Accuracy

L'agent choisit-il le bon skill quand un skill existe pour la tâche ?

- **Motivation** : autometa a 14 skills. Quand l'utilisateur demande "montre-moi les stats Matomo du Marché", l'agent devrait utiliser le skill `matomo_query`, pas un `Bash` avec curl
- **Implémentation** : annoter les gold avec `expected_skill`, comparer avec le skill effectivement invoqué
- **Score** : accuracy (correct skill / total invocations où un skill était attendu)

```python
def skill_routing_accuracy(
    actual_skills: list[str | None],
    expected_skills: list[str],
) -> dict[str, float]:
    """Returns {'accuracy': float, 'misroutes': list[dict]}."""
    ...
```

### 7. Knowledge Utilization Rate

L'agent lit-il la documentation pertinente avant de requêter ?

- **Motivation** : les fichiers `knowledge/sites/*.md` contiennent le contexte nécessaire (IDs Matomo, instances Metabase, vocabulaire métier). Un agent qui requête sans lire le knowledge risque des erreurs
- **Implémentation** : pour chaque conversation touchant un site (détecté via keywords ou site_id), vérifier si un `Read` du fichier knowledge correspondant précède le premier appel API
- **Score** : `n_knowledge_reads_before_api / n_conversations_needing_knowledge`

```python
def knowledge_utilization(
    tool_sequence: list[dict[str, str]],
    expected_knowledge_files: list[str],
) -> dict[str, float | bool]:
    """Returns {'utilized': bool, 'rate': float, 'missing_reads': list[str]}."""
    ...
```

### 8. Token Efficiency

Ratio de tokens utiles vs tokens totaux consommés.

- **Motivation** : le champ `message.usage` dans les sessions JSONL donne `input_tokens`, `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens`. Certaines sessions consomment beaucoup de tokens pour peu de valeur
- **Implémentation** : `useful_output_tokens / total_tokens` où `useful_output_tokens` = tokens dans les `text` blocks finaux (pas les thinking, pas les tool_use redondants)
- **Benchmark** : sessions gold annotées avec un flag "coût acceptable" vs "trop cher"

```python
def token_efficiency(
    session_usage: list[dict[str, int]],
    useful_output_tokens: int,
) -> dict[str, float]:
    """Returns {'efficiency': float, 'total_input': int, 'total_output': int, 'cache_hit_rate': float}."""
    ...
```

---

## Synthèse — métriques app-context recommandées

| Priorité | Métrique | Dimension | Automatisable ? |
|----------|----------|-----------|-----------------|
| 1 | SQL Result Correctness | Exactitude | Semi (gold requis) |
| 2 | Correction Rate (hybride) | Qualité interaction | Oui |
| 3 | SQL Schema Validity | Exactitude | Oui (catalogue DB) |
| 4 | Hallucination Signals | Fiabilité | Oui (inventaire sync) |
| 5 | Tool Chain Length | Efficience | Oui |
| 6 | Skill Routing Accuracy | Pertinence | Semi (gold requis) |
| 7 | SQL Execution Success | Exactitude | Oui (sandbox) |
| 8 | Knowledge Utilization | Bonnes pratiques | Oui |
| 9 | Path Optimality (proxies) | Pertinence | Semi (gold requis) |
| 10 | Token Efficiency | Coût | Oui |
| 11 | SQL Efficiency | Performance | Semi (gold requis) |
| 12 | SQL Style Conformity | Conventions | Oui (linter) |
