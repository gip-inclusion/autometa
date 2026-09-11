# Multi-moteurs : routage et rattrapage

Permettre à autometa de basculer sans couture entre plusieurs moteurs d'agent au fil d'une même
conversation, quand la fenêtre d'utilisation Claude est épuisée.

Statut : exploration terminée, plan en attente de validation. Aucune ligne de code écrite.

**Ce chantier touche une zone critique et nécessite une relecture humaine** — `web/models.py`,
`web/runner.py`, `web/agents/cli.py`, `alembic/`.

## 1. Le principe

Chaque moteur garde sa propre mémoire (sa session native, reprise avec `--resume`). Pour faire jouer
un tour à un moteur, on le reprend et on lui glisse **un seul message de rattrapage** : uniquement ce
qui s'est passé depuis la dernière fois qu'il a parlé.

Il n'y a pas d'opération « bascule », seulement du **routage** : suis-je bloqué ? alors tel moteur.
La mécanique est la même quel que soit le sens, donc il n'y a **pas** de chemin « Claude → secours »
distinct d'un chemin « secours → Claude ».

Le rattrapage est calculé à la volée et **n'est jamais écrit dans la table `messages`**. On n'y garde
que les tours natifs de chaque moteur. Conséquence : chaque session ne grossit que d'un épisode par
aller-retour, sans imbrication.

Le comportement actuel `Claude → Claude` est le cas dégénéré : rien ne s'est intercalé, le rattrapage
est vide, c'est un `--resume` natif. On généralise le système existant, on n'en ajoute pas un second.

## 2. Faits établis

Tout ce qui suit a été mesuré, pas supposé. La méthode est indiquée pour que ce soit rejouable.

### 2.1 Le moteur de secours retenu : Ollama Cloud

`https://ollama.com` sert `/v1/messages` au format Anthropic. Vérifié avec un contrôle négatif : un
chemin inexistant renvoie `{"error":"path ... not found"}`, alors que `/v1/messages` renvoie une
enveloppe Anthropic complète (`type: error`, `request_id`, validation du modèle).

| Vérification | Résultat |
|---|---|
| Authentification (`Authorization: Bearer <clé>`) | Fonctionne |
| Aller-retour agentique `tool_use` → `tool_result` → réponse | **Fonctionne** |
| Blocs `thinking` | Supportés |
| Fenêtre de contexte de `glm-5.2` (`/api/show`) | **1 048 576 tokens** |
| Capacités déclarées | `thinking`, `completion`, `tools` |
| Cache de prompt Anthropic | **Absent** |

Sur le cache : `cache_control` est accepté sans erreur, mais aucun champ `cache_creation_input_tokens`
ni `cache_read_input_tokens` n'est renvoyé, et `input_tokens` est identique sur deux appels successifs
avec le même préfixe. Il n'y a donc pas de cache de prompt facturé ni rapporté.

**Aucun proxy n'est nécessaire, et le format ne dépend pas du modèle.** `/v1/messages` est un endpoint
de passerelle d'Ollama Cloud : c'est lui qui traduit vers le format natif de chaque modèle. Changer de
modèle est donc une simple valeur de configuration, sans code.

| Modèle | Fenêtre | Appel d'outil réel |
|---|---|---|
| `glm-5.2` | 1 048 576 | Oui |
| `glm-5.3` | 1 048 576 | Oui |
| `glm-5.3-flash` | 1 048 576 | Oui |
| `kimi-k2.7-code` | 262 144 | Oui |
| `deepseek-v4-pro:0813` | 1 048 576 | Oui |
| `minimax-m3` | 512 000 | Oui |

Tous renvoient `stop_reason: tool_use` avec le bon argument, et déclarent `thinking`.

Catalogue au 2026-09-08 : `glm-5.3`, `glm-5.3-flash`, `glm-5.2`, `glm-5.1`, `kimi-k3`, `kimi-k2.7-code`,
`kimi-k2.6`, `deepseek-v4-pro:0813`, `deepseek-v4-flash:0731`, `minimax-m3`, `minimax-m2.7`,
`qwen3.5:397b`, `mistral-large-3:675b`, `nemotron-3-ultra`, `nemotron-3-super`, `nemotron-3-nano:30b`,
`gemma4:31b`, `gpt-oss:120b`, `gpt-oss:20b`.

### 2.2 Rejeu de la charge réelle du CLI

Les tests ci-dessus n'utilisaient qu'un outil écrit à la main. Pour aller plus loin, la requête
réellement émise par `web/agents/cli.py` a été capturée puis rejouée telle quelle contre Ollama Cloud,
en ne changeant que le modèle et la question.

| Ce qui est testé | Résultat |
|---|---|
| 7 schémas d'outils réels du CLI (`Bash` à 2 707 car, profondeur 4) | Acceptés |
| Prompt système `AGENT.md` + contexte `CLAUDE.md` injecté | Accepté |
| Champs propres au CLI (`thinking`, `context_management`, `output_config`) | Acceptés sans erreur |
| Charge d'entrée | 13 676 tokens |
| Appel d'outil sur schéma complexe | `Read` avec le bon argument |
| Streaming SSE | Séquence Anthropic conforme |

Le flux respecte exactement la séquence attendue par le CLI : `message_start`, `content_block_start`,
`content_block_delta` (dont `thinking_delta`), `content_block_stop`, `message_delta`, `message_stop`,
avec les `usage` dans `message_start`.

**Ce qui reste non testé** et doit être levé aux étapes 0 et 1 : l'enchaînement long (vingt à trente
appels d'outils à la file, où les modèles décrochent typiquement), `--resume` sur une session écrite
par ce modèle — le pivot du design — et la qualité analytique en français. À noter aussi que `glm-5.2`
émet des identifiants d'appel au format `call_…` et non `toolu_…` ; sans effet sur l'aller-retour
testé, à surveiller sur un parcours complet.

### 2.3 Le backend `cli-ollama` est cassé aujourd'hui

Trois défauts de configuration, tous vérifiés, qui font que `AGENT_BACKEND=cli-ollama` ne peut pas
fonctionner en l'état :

| Où | Valeur actuelle | Problème |
|---|---|---|
| `web/config.py` `OLLAMA_MODEL` | `qwen3-coder-next` | **Retiré le 2026-07-15**, l'API le dit explicitement |
| `web/config.py` `OLLAMA_BASE_URL` | `http://localhost:11434` | Vise une instance locale, pas le cloud |
| `web/agents/cli_ollama.py` | `ANTHROPIC_AUTH_TOKEN = "ollama"` | Jeton en dur, rejeté par le cloud |

### 2.4 Coût fixe du CLI

Mesuré en pointant `ANTHROPIC_BASE_URL` vers un serveur de capture local et en lisant la requête
réellement émise, pour un prompt « dis bonjour », dans la configuration autometa (MCP exclus, prompt
système réel). Comptage par tokenizer, pas par estimation de caractères.

| Poste | Tokens |
|---|---|
| Définitions d'outils (27) | 17 269 |
| Messages injectés (`CLAUDE.md`, `.claude/rules/`, liste des skills) | 13 501 |
| Prompt système (`AGENT.md` + index de contexte) | 5 497 |
| **Total** | **36 267** |

Face aux 1 048 576 tokens de `glm-5.2`, ce coût fixe pèse 3,5 %. **Il n'est donc pas un problème**, et
aucun profil d'outils réduit n'est nécessaire.

Ce chiffre reste consigné parce qu'il devient bloquant sur un moteur à petite fenêtre. Pour mémoire,
une instance Ollama locale sur un Mac 48 Go plafonne à 32 768 tokens : le coût fixe seul y représente
111 % de la fenêtre, et aucune conversation n'est possible. `--disallowedTools` retire réellement les
définitions de la requête (17 269 → 2 356 tokens sur 7 outils), ce qui ramène le total à 20 639 tokens.
C'est le levier à ressortir si un moteur local revient un jour au programme.

### 2.5 Coût du rattrapage

Mesuré sur trois vraies sessions autometa, découpées en épisodes (un épisode = d'un message
utilisateur au suivant).

| Politique | Médiane | p90 | Max |
|---|---|---|---|
| Rattrapage brut | 11 k car | 131 k car | 435 k car |
| Plafonné (entrée d'outil 300 B, résultat 1 000 B, total 30 k car) | **~1,5 k tokens** | — | **7,5 k tokens** |

L'affirmation « coût plat quel que soit le nombre d'allers-retours » est **vérifiée** : chaque session
ne grossit que d'un épisode par aller-retour, sans imbrication ni accumulation. Mais la distribution
des épisodes est très asymétrique — un épisode agentique lourd atteint 110 k tokens brut. Les plafonds
bornent le rattrapage par construction.

Avec une fenêtre de 1 M, ces plafonds ne sont plus une nécessité mais un garde-fou contre les cas
pathologiques. Ils restent au design à ce titre.

Réserve : ces sessions sont des sessions de développement, plus lourdes en outils qu'une conversation
analytique typique. Les chiffres autometa réels seront plus bas.

### 2.6 Ce qui est déjà en place et qu'on réutilise

- **Les actions sont déjà persistées.** `Message.type` vaut `user`, `assistant`, `tool_use`,
  `tool_result`, `limit`, `system`, et `content` porte le JSON de l'outil (`_serialize_tool_event`
  dans `web/runner.py`). Reconstruire un rattrapage avec les actions ne demande aucun stockage neuf.
- **Le signal de bascule existe.** `usage_limit_reset()` dans `web/agents/cli.py` parse la limite et le
  stream la range dans `outcome["usage_limit_reset"]`, remontée comme un `AgentMessage` de type `limit`.
- **Le canal partagé entre workers existe.** `_alert_usage_limit_once` (`web/runner.py`) utilise déjà
  une clé Redis à TTL pour dédupliquer une information de limite entre toutes les conversations.
- **L'ancêtre du rattrapage existe.** `history_for_turn` (`web/runner.py`) rend `[]` quand le fichier de
  session est là, et le transcript complet quand il manque.
- **L'instrument de comparaison de modèles existe.** `evals/run_eval.py --backends cli ollama
  --ollama-models` envoie des questions identiques à plusieurs backends. Il n'a jamais tourné.

## 3. Design retenu

### 3.1 Le routage

Une clé Redis globale porte l'état « ce moteur est bloqué » :

```
autometa:limit:<backend>   posée avec exat=<instant de reset>
```

Elle disparaît d'elle-même à l'heure de reprise : pas de cron, pas de colonne, pas de nettoyage, et
tous les workers la voient. C'est le même mécanisme que l'alerte Slack existante.

Le choix du moteur, avant chaque tour :

1. Si `AGENT_FALLBACK_BACKEND` n'est pas configuré → `AGENT_BACKEND`. **Comportement actuel inchangé.**
2. Si la clé du moteur primaire existe → moteur de secours.
3. Sinon → moteur primaire.

`get_agent()` prend un nom optionnel. `TaskRunner` cesse de garder un `self.backend` figé et choisit
par tour. Un cache d'instances par nom évite de respawner un objet backend à chaque tour.

Quand un événement `limit` remonte pendant un tour, le runner pose la clé et **rejoue le même tour sur
le moteur de secours**, une seule fois. Si le secours échoue aussi, on retombe sur le message de limite
actuel. Une seule re-route par tour, jamais de boucle.

Le retour sur le moteur primaire ne demande aucun code : la clé expire, la condition 2 devient fausse.

### 3.2 L'état par moteur

Une colonne JSONB sur `conversations` :

```
engine_state = {
  "cli":        {"session_id": "...", "seen_through": 1234},
  "cli-ollama": {"session_id": "...", "seen_through": 1230}
}
```

Les identifiants de moteur sont les valeurs `AGENT_BACKEND` déjà en usage, celles que
`usage_events.backend` enregistre.

**Pourquoi une colonne et pas une table** : deux lignes bornées par conversation, toujours chargées
avec le parent, jamais interrogées en travers des conversations. La règle est de normaliser ce qu'on
interroge et d'embarquer ce qui est un attribut du parent. Une table deviendra le bon choix le jour où
on voudra requêter dessus.

**Pourquoi `seen_through` est stocké et non dérivé** : les messages sont écrits en base *au fil du
stream*. Un repère dérivé du dernier message produit par le moteur avancerait donc tout seul pendant le
tour, et une limite frappant en plein stream figerait exactement le point corrompu qu'on veut éviter.
Un repère stocké ne s'écrit qu'à la fin d'un tour complet. C'est le point de vigilance nº 2 qui tranche.

**Sémantique du repère** : « dernier message que ce moteur a vu », pas « dernier message qu'il a
produit ». Le CLI écrit le prompt qu'on lui passe dans son propre `.jsonl` ; après un rattrapage, le
moteur a donc bien vu tout ce qu'il contenait. « Vu » est la sémantique correcte et la plus simple.

`Conversation.session_id` reste en place et continue de porter la session du moteur primaire, pour ne
rien casser. `engine_state` est la source de vérité ; s'il est vide, il est initialisé paresseusement
depuis `session_id`.

### 3.3 Le rattrapage

Calculé dans `history_for_turn`, qui devient le point unique :

| Situation | Ce que rend `history_for_turn` |
|---|---|
| Fichier de session présent, rien de nouveau | `[]` — cas dégénéré, comportement actuel |
| Fichier de session présent, un épisode s'est intercalé | Le rattrapage |
| Fichier de session absent | Le transcript complet — mode dégradé actuel |

Un `select()` sur `messages` avec `id > seen_through`, en gardant les types `user`, `assistant`,
`tool_use`, `tool_result`, et en écartant `system` et `limit` (du bruit). Les événements d'outils sont
rendus lisiblement dans le `content`.

Le résultat est une `list[dict]` au format `history` déjà attendu. **Et c'est là que le code maigrit.**
`web/agents/cli.py` fait aujourd'hui :

```python
if is_resume:
    prompt = message
else:
    prompt = self._build_prompt(message, history)
```

Or `_build_prompt` commence par `if not history: return message`. Ces quatre lignes se réduisent donc à
`prompt = self._build_prompt(message, history)` : strictement équivalent quand l'historique est vide,
déjà correct quand il ne l'est pas. Le rattrapage transite par le canal existant, la branche disparaît.

Plafonds : entrée d'outil 300 B, résultat d'outil 1 000 B, rattrapage entier 30 000 caractères en
gardant la fin. Chaque troncature est marquée explicitement dans le texte.

### 3.4 Dégradation

- **Session absente ou purgée de S3** → `history_for_turn` rend le transcript complet, exactement comme
  aujourd'hui. Dégradation, jamais casse.
- **Moteur de secours injoignable** → une seule tentative, puis le message de limite actuel.
- **Moteur de secours non configuré** → la fonctionnalité est éteinte, comportement actuel à
  l'identique. C'est le défaut.

### 3.5 Configuration

| Variable | Défaut | Rôle |
|---|---|---|
| `AGENT_FALLBACK_BACKEND` | `""` | Moteur de secours. Vide = fonctionnalité éteinte |
| `OLLAMA_BASE_URL` | à corriger en `https://ollama.com` | Base de l'API |
| `OLLAMA_MODEL` | à corriger, `qwen3-coder-next` est retiré | Modèle servi |
| `OLLAMA_API_KEY` | `""` | Jeton, aujourd'hui en dur à `"ollama"` |

Toute lecture passe par `web/config.py`, sans exception.

## 4. Alternatives écartées

**Une session `.jsonl` partagée entre les deux moteurs.** Coûterait zéro migration, et le format le
permet : les deux moteurs écrivent le même format dans le même dossier, avec `message.model` par tour.
Écartée pour trois raisons. L'auto-compaction réécrit l'historique en le résumant — sur un fichier
partagé, elle détruit la mémoire du premier moteur et invalide son cache, c'est-à-dire précisément la
réécriture qu'il ne faut jamais faire. Un `--resume` partagé donne tout l'historique d'un moteur à
l'autre, sans contrôle. Et un fichier corrompu l'est pour les deux à la fois, sans état sain vers
lequel retomber. Deux sessions séparées coûtent une colonne : c'est le prix de l'isolation.

**Rejouer tout l'historique depuis la base à chaque tour** (le modèle sans état de LiteLLM ou
OpenRouter). Écartée sur deux motifs. Mesuré : 32 à 193 k tokens par tour sur nos vraies conversations.
Et c'est un redesign du fonctionnement entier, alors que le besoin est de ne changer que le point de
bascule.

**Dériver le repère au lieu de le stocker.** Écartée : les messages étant écrits au fil du stream, la
dérivation avance le repère sur un tour interrompu. Voir 3.2.

**Une table `conversation_engines`.** Écartée : deux lignes bornées, toujours chargées avec le parent,
jamais interrogées en travers. Voir 3.2.

**Coder deux chemins de bascule.** C'est le piège à éviter. Le design a une fonction qui choisit un
moteur et une fonction qui calcule un rattrapage ; ni l'une ni l'autre ne sait dans quel sens on va.

**Un moteur local (Ollama sur la machine).** Écarté pour cet usage : 32 768 tokens de fenêtre sur un
Mac 48 Go, contre 36 267 de coût fixe. Impossible sans profil d'outils réduit, et indisponible en
production de toute façon. Voir 2.4 pour le levier si la question revient.

## 5. Réponses aux questions d'exploration

1. **Où vit le moteur courant ?** Par tour, décidé dans le runner à partir d'une clé Redis. Pas de
   notion de « moteur courant » persistée : c'est du routage, pas un état.
2. **Le routage.** Déclenché par l'événement `limit` déjà produit par `usage_limit_reset`. Le retour se
   fait par expiration de la clé. Moteur de secours injoignable : une tentative, puis message actuel.
3. **Le stockage de l'état.** Colonne JSONB `engine_state`. `fork_conversation` copie chaque session
   listée et recopie le blob.
4. **Le format du rattrapage.** Reconstruit depuis `messages`, où `tool_use` et `tool_result` sont
   **déjà persistés**. Aucun stockage supplémentaire.
5. **Le repère.** Stocké dans `engine_state`, écrit uniquement à la fin d'un tour complet.
6. **La dégradation.** `history_for_turn` généralisé, pas doublé.
7. **Le cache.** Le design le préserve structurellement : chaque session est strictement en ajout, donc
   le préfixe déjà mis en cache n'est jamais invalidé. Mais dans le scénario réel, **ça ne sert à
   rien** : le cache Anthropic expire en 5 minutes alors qu'on bascule pour attendre un reset qui dure
   des heures, et Ollama Cloud n'a pas de cache de prompt du tout. Le design ne dégrade rien ; l'objectif
   « utiliser le cache des uns et des autres » n'est pas atteignable dans ce scénario.
8. **Le coût réel.** « Coût plat » vérifié. Voir 2.5, avec la nuance sur l'asymétrie des épisodes.

## 6. Plan d'implémentation

En TDD, un test avant chaque comportement.

**Étape 0 — Réparer `cli-ollama`.** Corriger les trois défauts de 2.3 : modèle retiré, base URL locale,
jeton en dur. Rendre le jeton et la base configurables via `web/config.py`. Sans cela le moteur de
secours ne démarre pas. Indépendant du reste, mergeable seul.

**Étape 1 — Choisir le modèle.** Faire tourner `evals/run_eval.py` sur les candidats du catalogue
(`glm-5.2`, `glm-5.3`, `kimi-k2.7-code`, `deepseek-v4-pro`) et retenir celui qui tient sur des questions
analytiques en français. Produit une valeur pour `OLLAMA_MODEL`, pas du code.

**Étape 2 — Le routage.** `get_agent(name)`, la clé Redis, le choix par tour dans `TaskRunner`. Sans le
rejeu ni le rattrapage : à ce stade le moteur de secours démarre une session neuve. Vérifiable seul.

**Étape 3 — Le schéma.** `engine_state` dans `web/models.py`, `alembic revision --autogenerate`,
relecture de la migration générée, `alembic upgrade head`. Ajouter `engine_state` à l'allowlist de
`update_conversation` (`web/stores/conversations.py`). Étendre `fork_conversation` pour copier chaque
session et le blob.

**Étape 4 — Le rattrapage.** Généraliser `history_for_turn`, supprimer la branche `is_resume` de
`web/agents/cli.py`, écrire le rendu des événements d'outils et les plafonds. Écrire `seen_through` en
fin de tour complet.

**Étape 5 — Le rejeu du tour perdu.** La boucle de re-route dans `_run_agent`, une seule tentative.

**Étape 6 — Observabilité.** `agent_backend` est aujourd'hui lu depuis `config.AGENT_BACKEND` pour les
spans, les tags Sentry et `insert_usage_event`. Passer le moteur réellement utilisé, sinon les
statistiques d'usage attribuent au mauvais moteur.

## 7. Tests à écrire

Marqueurs : tout ce qui suit tourne sans service sauf mention contraire.

**Routage** — `parametrize` sur (clé présente ou non) × (secours configuré ou non) : le moteur choisi.
Cas « secours non configuré » : le comportement actuel est rendu à l'identique. Cache d'instances : deux
appels rendent la même instance.

**Clé Redis** — posée avec le bon instant d'expiration à la réception d'un événement `limit`.
`@pytest.mark.integration`.

**Rattrapage** — `parametrize` sur les trois situations de 3.3. Rendu des `tool_use`/`tool_result`.
Plafonds : entrée, résultat, total, avec marque de troncature. Types `system` et `limit` écartés.

**Repère** — avancé en fin de tour complet ; **non avancé** quand le tour est coupé par une limite.
C'est le test qui protège le point de vigilance nº 2.

**`cli.py`** — après suppression de la branche : reprise avec historique vide → le prompt est le message
seul (non-régression) ; reprise avec rattrapage → prompt combiné.

**Rejeu** — un événement `limit` déclenche une seule re-route ; un échec du secours rend le message de
limite ; pas de seconde re-route si le tour tournait déjà sur le secours.

**Fork** — `engine_state` recopié, chaque session copiée.

**Observabilité** — `insert_usage_event` reçoit le moteur réellement utilisé, pas `config.AGENT_BACKEND`.

**Bout en bout** — `@pytest.mark.external` : un tour réel contre Ollama Cloud avec un appel d'outil.
Aucune CI ne l'exécute aujourd'hui.

## 8. Impacts

**Migration.** Une révision Alembic additive : `engine_state` JSONB nullable sur `conversations`.
Réversible, sans backfill — un `engine_state` vide est initialisé paresseusement depuis `session_id`.

**Zones critiques touchées**, toutes en relecture humaine : `web/models.py` (schéma),
`web/runner.py` (orchestration), `web/agents/cli.py` (intégration externe), `alembic/`.

**Apps interactives.** `lib.query`, `web.db`, `web.config` ne changent pas de signature. `data/interactive/`
n'est pas impacté.

**Réversibilité.** `AGENT_FALLBACK_BACKEND` vide éteint toute la fonctionnalité et rend le comportement
actuel. La colonne peut rester en place sans être lue.

**Données et destinataires.** Le moteur de secours introduit un destinataire hors Anthropic. Ce qui
sort vers lui : le message de l'utilisateur, les réponses de l'agent, et le rendu borné des appels et
résultats d'outils — donc des extraits des bases interrogées, qui portent des données de candidats à
l'IAE. Deux garde-fous : tout ce qui part passe par les plafonds de `web/catchup.py`, y compris
l'amorçage d'une session neuve (un transcript complet non borné partait auparavant au premier
basculement) ; et la cible Ollama n'est distante que si `OLLAMA_API_KEY` est renseignée, l'instance
locale restant le défaut, pour qu'aucun déploiement ne se mette à sortir du réseau par héritage.
La bascule reste muette côté utilisateur — décision produit assumée : le tour n'est pas perdu, donc
rien ne justifie d'interrompre la lecture. Côté exploitation en revanche, chaque reroutage et chaque
amorçage de session sont journalisés, ce dernier avec sa taille. Activer `AGENT_FALLBACK_BACKEND` en
production suppose donc un arbitrage explicite sur ce destinataire, qui n'est pas un sous-traitant
déclaré du service.
