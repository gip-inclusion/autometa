# Multi-moteurs : routage et rattrapage — plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permettre à une conversation de basculer entre le moteur Claude et un moteur de secours quand la limite d'usage est atteinte, chaque moteur gardant sa session native et recevant un message de rattrapage calculé à la volée.

**Architecture:** Pas d'opération « bascule » : un choix de moteur par tour à partir d'une clé Redis à TTL, et un rattrapage calculé depuis la table `messages` qui transite par le canal `history` existant. Le comportement actuel est le cas dégénéré (rattrapage vide). Un seul mécanisme, valable dans les deux sens.

**Tech Stack:** Python 3.14, SQLAlchemy 2.0, Alembic, Redis (redis.asyncio), pytest + pytest-mock, uv.

**Spec:** `docs/plans/multi-moteurs-rattrapage.md`

## Global Constraints

- Toutes les commandes passent par `uv run --frozen ...`. Suite unit : `make test`. Lint : `make lint`.
- **Zones critiques** (`.claude/rules/zones-critiques.md`) : `web/models.py`, `web/runner.py`, `web/agents/cli.py`, `alembic/`. Toute tâche qui les touche exige une relecture humaine et doit le signaler.
- Imports en tête de module, jamais d'imports relatifs parents (`from web.x import ...`, pas `from ..x import`).
- Pas de commentaires descriptifs. `# Why:` uniquement quand l'intention n'est pas déductible. Docstrings d'une ligne maximum.
- Jamais de f-string dans `logger.*()` — formatage paramétré : `logger.info("msg %s", var)`.
- Toute lecture de variable d'environnement passe par `web/config.py`, sans exception.
- pytest seul, jamais `unittest`. Mocks via le fixture `mocker` de pytest-mock. `@pytest.mark.parametrize` dès qu'un même comportement varie d'entrée. Fonctions usine plutôt que fixtures sans état.
- Un test non marqué doit tourner sans service. `@pytest.mark.integration` si Postgres ou Redis est requis. `@pytest.mark.external` pour les vrais services distants.
- Jamais de SQL non paramétré. Jamais de modification d'une migration existante.
- Messages de commit en anglais, concis. **Ne jamais `git push`.**

## Structure des fichiers

| Fichier | Responsabilité | Tâches |
|---|---|---|
| `web/config.py` | Nouvelles variables `AGENT_FALLBACK_BACKEND`, `OLLAMA_API_KEY` ; correction des défauts Ollama | 1, 3 |
| `web/agents/cli_ollama.py` | Jeton d'authentification configurable | 1 |
| `web/agents/__init__.py` | `get_agent(backend)` avec cache d'instances | 2 |
| `web/runner.py` | Routage, choix par tour, rejeu, écriture du repère, `history_for_turn` généralisé | 3, 6, 7, 8, 9 |
| `web/models.py` | Colonne `engine_state` | 4 |
| `alembic/versions/` | Migration additive | 4 |
| `web/stores/records.py` | Champ `engine_state` du dataclass, allowlist | 4 |
| `web/stores/conversations.py` | Lecture/écriture de `engine_state`, fork | 4 |
| `web/catchup.py` | **Nouveau.** Rendu du rattrapage et plafonds. Fonction pure, sans I/O | 5 |

`web/catchup.py` est un module neuf plutôt qu'un ajout à `web/runner.py` : c'est une soixantaine de lignes de rendu et de troncature, sans I/O, donc testable sans aucun mock — alors que `runner.py` fait déjà 635 lignes et est une zone critique. Les fonctions de routage, elles, restent dans `runner.py` au niveau module, à côté de `history_for_turn`, parce que c'est le pattern déjà en place dans ce fichier.

---

### Task 1: Réparer le backend `cli-ollama`

Trois défauts vérifiés empêchent `AGENT_BACKEND=cli-ollama` de fonctionner : le modèle `qwen3-coder-next` a été retiré le 2026-07-15, `OLLAMA_BASE_URL` vise `localhost` au lieu d'Ollama Cloud, et le jeton est codé en dur à `"ollama"`. Tâche indépendante du reste, mergeable seule.

**Files:**
- Modify: `web/config.py` (bloc Ollama, ~l.65-69)
- Modify: `web/agents/cli_ollama.py`
- Modify: `.env.example` (~l.163-169)
- Test: `tests/test_backend_cli_ollama.py`

**Interfaces:**
- Consomme : rien.
- Produit : `config.OLLAMA_API_KEY: str`, `config.OLLAMA_BASE_URL` par défaut `"https://ollama.com"`, `config.OLLAMA_MODEL` par défaut `"glm-5.2"`.

- [ ] **Step 1: Écrire les tests en échec**

Remplacer `test_build_env_sets_ollama_vars` (qui vérifie le jeton en dur) dans `tests/test_backend_cli_ollama.py` :

```python
import pytest

from web.agents.cli_ollama import CLIOllamaBackend


@pytest.mark.parametrize(
    "api_key, expected_token",
    [("sk-abc", "sk-abc"), ("", "ollama")],
)
def test_build_env_uses_configured_api_key(mocker, api_key, expected_token):
    mock_config = mocker.patch("web.agents.cli_ollama.config")
    mock_config.OLLAMA_BASE_URL = "https://ollama.com"
    mock_config.OLLAMA_API_KEY = api_key
    env = CLIOllamaBackend()._build_env()

    assert env["ANTHROPIC_BASE_URL"] == "https://ollama.com"
    assert env["ANTHROPIC_AUTH_TOKEN"] == expected_token
    assert env["ANTHROPIC_API_KEY"] == ""
```

Et dans `tests/test_config.py` :

```python
def test_ollama_defaults_target_cloud():
    from web import config

    assert config.OLLAMA_BASE_URL == "https://ollama.com"
    assert config.OLLAMA_MODEL == "glm-5.2"
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `DATABASE_URL= REDIS_URL= uv run --frozen pytest tests/test_backend_cli_ollama.py tests/test_config.py::test_ollama_defaults_target_cloud -v`
Expected: FAIL — `AttributeError` sur `OLLAMA_API_KEY`, et assertion sur `ANTHROPIC_AUTH_TOKEN`.

- [ ] **Step 3: Corriger la configuration**

Dans `web/config.py`, remplacer le bloc Ollama :

```python
# Ollama Cloud (moteur de secours). qwen3-coder-next a été retiré le 2026-07-15.
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "https://ollama.com")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "glm-5.2")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")
OLLAMA_TITLE_MODEL = os.getenv("OLLAMA_TITLE_MODEL", OLLAMA_MODEL)
OLLAMA_TAG_MODEL = os.getenv("OLLAMA_TAG_MODEL", OLLAMA_MODEL)
OLLAMA_REQUEST_TIMEOUT = float(os.getenv("OLLAMA_REQUEST_TIMEOUT", "120"))
```

Dans `web/agents/cli_ollama.py`, remplacer le corps de `_build_env` :

```python
    def _build_env(self, *, conversation_id: str | None = None, user_email: str | None = None) -> dict:
        env = super()._build_env(conversation_id=conversation_id, user_email=user_email)
        env["ANTHROPIC_BASE_URL"] = config.OLLAMA_BASE_URL
        # Why: une instance Ollama locale ignore le jeton ; Ollama Cloud le rejette s'il est vide.
        env["ANTHROPIC_AUTH_TOKEN"] = config.OLLAMA_API_KEY or "ollama"
        env["ANTHROPIC_API_KEY"] = ""
        return env
```

Dans `.env.example`, remplacer le bloc Ollama :

```
# Ollama Cloud (moteur de secours, AGENT_FALLBACK_BACKEND=cli-ollama)
OLLAMA_BASE_URL=https://ollama.com
OLLAMA_MODEL=glm-5.2
OLLAMA_API_KEY=
```

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

Run: `DATABASE_URL= REDIS_URL= uv run --frozen pytest tests/test_backend_cli_ollama.py tests/test_config.py -v && make lint`
Expected: PASS, lint sans erreur.

- [ ] **Step 5: Commit**

```bash
git add web/config.py web/agents/cli_ollama.py .env.example tests/test_backend_cli_ollama.py tests/test_config.py
git commit -m "fix(ollama): target Ollama Cloud with a configurable API key"
```

---

### Task 2: `get_agent()` par nom, avec cache d'instances

**Files:**
- Modify: `web/agents/__init__.py`
- Test: `tests/test_backend.py`

**Interfaces:**
- Consomme : rien.
- Produit : `get_agent(backend: str | None = None) -> AgentBackend`. Deux appels avec le même nom rendent la **même** instance. `backend=None` utilise `config.AGENT_BACKEND`.

- [ ] **Step 1: Écrire les tests en échec**

Ajouter à `tests/test_backend.py` :

```python
def test_get_agent_accepts_explicit_backend():
    from web.agents import get_agent
    from web.agents.cli_ollama import CLIOllamaBackend

    assert isinstance(get_agent("cli-ollama"), CLIOllamaBackend)


def test_get_agent_reuses_instance_per_backend():
    from web.agents import get_agent

    assert get_agent("cli") is get_agent("cli")
    assert get_agent("cli") is not get_agent("cli-ollama")
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `DATABASE_URL= REDIS_URL= uv run --frozen pytest tests/test_backend.py -v`
Expected: FAIL — `get_agent()` ne prend pas d'argument, et rend une instance neuve à chaque appel.

- [ ] **Step 3: Écrire l'implémentation minimale**

Remplacer `get_agent` dans `web/agents/__init__.py` :

```python
_BACKENDS = {"cli": CLIBackend, "cli-ollama": CLIOllamaBackend}
_instances: dict[str, AgentBackend] = {}


def get_agent(backend: str | None = None) -> AgentBackend:
    name = backend or config.AGENT_BACKEND
    if name not in _BACKENDS:
        raise ValueError(f"Unknown AGENT_BACKEND: {name}")
    # Why: le backend porte la table des sous-processus en cours ; une instance neuve par tour
    # perdrait la trace des processus à annuler.
    if name not in _instances:
        _instances[name] = _BACKENDS[name]()
    return _instances[name]
```

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

Run: `DATABASE_URL= REDIS_URL= uv run --frozen pytest tests/test_backend.py -v`
Expected: PASS (les tests existants `test_get_agent` et l'erreur sur backend inconnu passent toujours).

- [ ] **Step 5: Commit**

```bash
git add web/agents/__init__.py tests/test_backend.py
git commit -m "feat(agents): select backend by name with a per-name instance cache"
```

---

### Task 3: Routage — clé Redis et choix du moteur par tour

**Zone critique : `web/runner.py`. À signaler en relecture.**

**Files:**
- Modify: `web/config.py` (ajout d'une variable)
- Modify: `web/runner.py` (fonctions module, `TaskRunner.__init__`, `_run_agent`, `cancel`, `_listen_cancel`)
- Test: `tests/test_runner_routing.py` (créer)

**Interfaces:**
- Consomme : `get_agent(backend)` de la tâche 2.
- Produit :
  - `config.AGENT_FALLBACK_BACKEND: str` (défaut `""` = fonctionnalité éteinte)
  - `runner.limit_key(backend: str) -> str`
  - `async runner.mark_backend_limited(backend: str, reset_iso: str | None) -> None`
  - `async runner.pick_backend() -> str`

- [ ] **Step 1: Écrire les tests en échec**

Créer `tests/test_runner_routing.py` :

Le projet n'a **aucun plugin pytest async** : le pattern maison est un test synchrone qui enveloppe un `async def _run()` et l'exécute avec `asyncio.run`. C'est celui de `tests/test_runner.py`, à reprendre tel quel. La fixture `fake_redis` s'appuie sur `fakeredis.aioredis.FakeRedis`, déjà utilisée dans la suite.

```python
"""Tests du routage multi-moteurs — choix du moteur et verrou de limite d'usage."""

import asyncio
from datetime import datetime, timedelta, timezone

import fakeredis.aioredis
import pytest

from web import runner


@pytest.fixture
def fake_redis():
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


@pytest.mark.parametrize(
    "fallback, blocked, expected",
    [
        ("", False, "cli"),
        ("", True, "cli"),
        ("cli-ollama", False, "cli"),
        ("cli-ollama", True, "cli-ollama"),
    ],
)
def test_pick_backend(mocker, fake_redis, fallback, blocked, expected):
    mocker.patch("web.runner.config.AGENT_BACKEND", "cli")
    mocker.patch("web.runner.config.AGENT_FALLBACK_BACKEND", fallback)
    mocker.patch("web.runner.get_redis", return_value=fake_redis)

    async def _run():
        if blocked:
            await fake_redis.set(runner.limit_key("cli"), "1")
        assert await runner.pick_backend() == expected

    asyncio.run(_run())


def test_pick_backend_skips_redis_without_fallback(mocker):
    mocker.patch("web.runner.config.AGENT_BACKEND", "cli")
    mocker.patch("web.runner.config.AGENT_FALLBACK_BACKEND", "")
    spy = mocker.patch("web.runner.get_redis")

    async def _run():
        assert await runner.pick_backend() == "cli"

    asyncio.run(_run())
    spy.assert_not_called()


def test_mark_backend_limited_sets_key_expiring_at_reset(mocker, fake_redis):
    mocker.patch("web.runner.get_redis", return_value=fake_redis)
    reset = datetime.now(timezone.utc) + timedelta(hours=3)

    async def _run():
        await runner.mark_backend_limited("cli", reset.isoformat())
        assert await fake_redis.exists(runner.limit_key("cli"))
        ttl = await fake_redis.ttl(runner.limit_key("cli"))
        assert 3 * 3600 - 60 < ttl <= 3 * 3600

    asyncio.run(_run())


def test_mark_backend_limited_ignores_missing_reset(mocker, fake_redis):
    mocker.patch("web.runner.get_redis", return_value=fake_redis)

    async def _run():
        await runner.mark_backend_limited("cli", None)
        assert await fake_redis.keys("*") == []

    asyncio.run(_run())
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `DATABASE_URL= REDIS_URL= uv run --frozen pytest tests/test_runner_routing.py -v`
Expected: FAIL — `AttributeError: module 'web.runner' has no attribute 'limit_key'`.

- [ ] **Step 3: Écrire l'implémentation minimale**

Dans `web/config.py`, sous `AGENT_BACKEND` :

```python
# Moteur de secours quand la limite d'usage du moteur principal est atteinte. Vide = désactivé.
AGENT_FALLBACK_BACKEND = os.getenv("AGENT_FALLBACK_BACKEND", "").strip().lower()
```

Dans `web/runner.py`, ajouter au niveau module (à côté de `history_for_turn`) :

```python
def limit_key(backend: str) -> str:
    return f"{PREFIX}:limit:{backend}"


async def mark_backend_limited(backend: str, reset_iso: str | None) -> None:
    """Marque un moteur comme bloqué jusqu'à son instant de reprise."""
    if not reset_iso:
        return
    r = await get_redis()
    await r.set(limit_key(backend), "1", exat=int(datetime.fromisoformat(reset_iso).timestamp()))


async def pick_backend() -> str:
    """Moteur à utiliser pour le prochain tour."""
    primary = config.AGENT_BACKEND
    if not config.AGENT_FALLBACK_BACKEND:
        return primary
    r = await get_redis()
    if await r.exists(limit_key(primary)):
        return config.AGENT_FALLBACK_BACKEND
    return primary
```

Dans `TaskRunner.__init__`, supprimer `self.backend = get_agent()`.

Dans `_run_agent`, au début du corps (avant `parent_ctx = ...`) :

```python
        backend_name = await pick_backend()
        backend = get_agent(backend_name)
```

Puis remplacer `self.backend.send_message(` par `backend.send_message(` et `await self.backend.cancel(conversation_id)` (branche du budget d'outils) par `await backend.cancel(conversation_id)`.

Dans `cancel` et `_listen_cancel`, remplacer `self.backend.cancel(conv_id)` par une annulation sur les deux moteurs possibles — le tour peut tourner sur l'un ou l'autre, et `cancel` rend `False` si le moteur ne connaît pas la conversation :

```python
    async def _cancel_all_backends(self, conv_id: str) -> bool:
        names = {config.AGENT_BACKEND}
        if config.AGENT_FALLBACK_BACKEND:
            names.add(config.AGENT_FALLBACK_BACKEND)
        results = [await get_agent(name).cancel(conv_id) for name in names]
        return any(results)
```

`cancel` appelle `await self._cancel_all_backends(conv_id)`, `_listen_cancel` aussi.

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

Run: `DATABASE_URL= REDIS_URL= uv run --frozen pytest tests/test_runner_routing.py tests/test_runner.py tests/test_backend.py -v`
Expected: PASS.

- [ ] **Step 5: Vérifier la non-régression complète et commiter**

Run: `make lint && make test`
Expected: lint sans erreur, suite unit verte.

```bash
git add web/config.py web/runner.py tests/test_runner_routing.py
git commit -m "feat(runner): pick the agent backend per turn from a Redis usage-limit lock"
```

---

### Task 4: Schéma — colonne `engine_state`

**Zones critiques : `web/models.py` et `alembic/`. À signaler en relecture.**

Le repère est un identifiant de message. Au fork, les messages sont réinsérés avec de nouveaux identifiants auto-incrémentés : le repère doit donc être **remappé par position**, pas recopié tel quel.

**Files:**
- Modify: `web/models.py` (classe `Conversation`)
- Create: `alembic/versions/<hash>_conversation_engine_state.py` (généré)
- Modify: `web/stores/records.py` (dataclass `Conversation`, `VALID_CONVERSATION_COLUMNS`, `conv_with_report_row`)
- Modify: `web/stores/conversations.py` (`get_conversation`, `update_conversation`, `fork_conversation`, nouvelles méthodes)
- Test: `tests/test_engine_state.py` (créer)

**Interfaces:**
- Consomme : rien.
- Produit :
  - `Conversation.engine_state: Mapped[dict | None]` (JSONB), et le champ `engine_state: Optional[dict] = None` sur le dataclass.
  - `store.get_engine_state(conv_id: str, backend: str) -> dict` — rend `{"session_id": str | None, "seen_through": int | None}`. Retombe sur `Conversation.session_id` pour le moteur `config.AGENT_BACKEND` quand le blob est vide.
  - `store.set_engine_state(conv_id: str, backend: str, *, session_id: str | None = None, seen_through: int | None = None) -> bool` — fusion partielle, n'écrase pas les clés non fournies.

- [ ] **Step 1: Écrire les tests en échec**

Créer `tests/test_engine_state.py` :

```python
"""Tests de l'état par moteur porté par conversations.engine_state."""

import pytest

from web.database import store

pytestmark = pytest.mark.integration


def _conv():
    return store.create_conversation(user_id="u1").id


def test_engine_state_falls_back_to_session_id_for_primary(mocker):
    mocker.patch("web.stores.conversations.config.AGENT_BACKEND", "cli")
    conv_id = _conv()
    store.update_conversation(conv_id, session_id="sess-1")

    assert store.get_engine_state(conv_id, "cli") == {"session_id": "sess-1", "seen_through": None}
    assert store.get_engine_state(conv_id, "cli-ollama") == {"session_id": None, "seen_through": None}


def test_set_engine_state_merges_without_clobbering():
    conv_id = _conv()
    store.set_engine_state(conv_id, "cli-ollama", session_id="sess-2")
    store.set_engine_state(conv_id, "cli-ollama", seen_through=42)

    assert store.get_engine_state(conv_id, "cli-ollama") == {"session_id": "sess-2", "seen_through": 42}


def test_engines_keep_independent_state():
    conv_id = _conv()
    store.set_engine_state(conv_id, "cli", session_id="a", seen_through=10)
    store.set_engine_state(conv_id, "cli-ollama", session_id="b", seen_through=7)

    assert store.get_engine_state(conv_id, "cli")["seen_through"] == 10
    assert store.get_engine_state(conv_id, "cli-ollama")["seen_through"] == 7


def test_fork_remaps_seen_through_by_position(mocker):
    mocker.patch("web.stores.conversations.session_sync.copy_session", return_value=True)
    conv_id = _conv()
    first = store.add_message(conv_id, "user", "un")
    second = store.add_message(conv_id, "assistant", "deux")
    store.add_message(conv_id, "user", "trois")
    store.update_conversation(conv_id, session_id="sess-src")
    store.set_engine_state(conv_id, "cli", session_id="sess-src", seen_through=second.id)

    forked = store.fork_conversation(conv_id, "u2")

    remapped = store.get_engine_state(forked.id, "cli")["seen_through"]
    assert remapped == forked.messages[1].id
    assert remapped != second.id or first.id == forked.messages[0].id
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `uv run --frozen pytest tests/test_engine_state.py -v`
Expected: FAIL — `AttributeError: 'Database' object has no attribute 'get_engine_state'`.

- [ ] **Step 3: Ajouter la colonne au modèle et générer la migration**

Dans `web/models.py`, classe `Conversation`, après `session_id` :

```python
    engine_state: Mapped[dict | None] = mapped_column(JSONB)
```

`JSONB` est déjà importé dans ce fichier.

```bash
make migrate
uv run --frozen alembic revision --autogenerate -m "conversation engine state"
```

Relire la migration générée : elle doit contenir exactement un `op.add_column` sur `conversations` avec une colonne `engine_state` JSONB nullable, et le `op.drop_column` correspondant dans `downgrade`. Rien d'autre. Supprimer toute instruction parasite qu'Alembic aurait ajoutée sur d'autres tables.

```bash
uv run --frozen alembic upgrade head
```

- [ ] **Step 4: Étendre le store**

Dans `web/stores/records.py` : ajouter `"engine_state"` à `VALID_CONVERSATION_COLUMNS`, ajouter `engine_state: Optional[dict] = None` au dataclass `Conversation` (après `session_id`), et `engine_state=row.engine_state` dans `conv_with_report_row`.

Dans `web/stores/conversations.py` : ajouter `from web import config` aux imports, `engine_state=c.engine_state` dans le `Conversation(...)` de `get_conversation`, et `"engine_state"` à l'allowlist de `update_conversation` (l.349).

Ajouter les deux méthodes au mixin :

```python
    def get_engine_state(self, conv_id: str, backend: str) -> dict:
        """État d'un moteur : identifiant de sa session native et dernier message qu'il a vu."""
        with get_db() as session:
            c = session.get(ConvModel, conv_id)
            if not c:
                return {"session_id": None, "seen_through": None}
            entry = (c.engine_state or {}).get(backend)
            if entry is None:
                # Why: avant la migration multi-moteurs, la session du moteur principal vivait
                # dans conversations.session_id — on la reprend au lieu d'en ouvrir une neuve.
                if backend == config.AGENT_BACKEND:
                    return {"session_id": c.session_id, "seen_through": None}
                return {"session_id": None, "seen_through": None}
            return {"session_id": entry.get("session_id"), "seen_through": entry.get("seen_through")}

    def set_engine_state(
        self,
        conv_id: str,
        backend: str,
        *,
        session_id: str | None = None,
        seen_through: int | None = None,
    ) -> bool:
        with get_db() as session:
            c = session.get(ConvModel, conv_id)
            if not c:
                return False
            state = dict(c.engine_state or {})
            entry = dict(state.get(backend) or {})
            if session_id is not None:
                entry["session_id"] = session_id
            if seen_through is not None:
                entry["seen_through"] = seen_through
            state[backend] = entry
            c.engine_state = state
            c.updated_at = utcnow()
            return True
```

Dans `fork_conversation`, remplacer le bloc de copie de session et l'insertion des messages :

```python
        new_engine_state = {}
        for backend, entry in (source.engine_state or {}).items():
            src_session = entry.get("session_id")
            if not src_session:
                continue
            candidate = str(uuid.uuid4())
            if session_sync.copy_session(src_session, candidate):
                new_engine_state[backend] = {"session_id": candidate, "seen_through": None}

        new_session_id = None
        if source.session_id:
            candidate = str(uuid.uuid4())
            if session_sync.copy_session(source.session_id, candidate):
                new_session_id = candidate
```

Puis, après l'insertion des messages, remapper les repères par position — les identifiants sont réattribués, donc un repère recopié tel quel désignerait un message d'une autre conversation :

```python
            session.add(model)

            old_ids = [m.id for m in source.messages]
            new_msgs = []
            for msg in source.messages:
                new_msg = MsgModel(
                    conversation_id=new_id,
                    type=msg.type,
                    role=msg.type,
                    content=msg.content,
                    timestamp=msg.created_at,
                )
                session.add(new_msg)
                new_msgs.append(new_msg)
            session.flush()

            for backend, entry in new_engine_state.items():
                old_seen = ((source.engine_state or {}).get(backend) or {}).get("seen_through")
                if old_seen in old_ids:
                    entry["seen_through"] = new_msgs[old_ids.index(old_seen)].id
            model.engine_state = new_engine_state or None
```

Et `model` reçoit `session_id=new_session_id` comme aujourd'hui.

- [ ] **Step 5: Lancer les tests pour vérifier qu'ils passent**

Run: `uv run --frozen pytest tests/test_engine_state.py tests/test_database.py -v`
Expected: PASS.

- [ ] **Step 6: Vérifier la cohérence du schéma et commiter**

Run: `uv run --frozen alembic check && make lint && make test`
Expected: `alembic check` sans divergence, lint propre, suite unit verte.

```bash
git add web/models.py alembic/versions web/stores/records.py web/stores/conversations.py tests/test_engine_state.py
git commit -m "feat(db): add per-engine session state to conversations"
```

---

### Task 5: Le rendu du rattrapage

Fonction pure, sans I/O. Rend une `list[dict]` au format `history` déjà attendu par `_build_prompt`, de sorte que le rattrapage transite par le canal existant.

**Files:**
- Create: `web/catchup.py`
- Test: `tests/test_catchup.py` (créer)

**Interfaces:**
- Consomme : les dataclasses `Message` de `web.stores.records` (attributs `id`, `type`, `content`).
- Produit : `build_catchup(messages: list) -> list[dict]`, chaque élément `{"role": "user" | "assistant", "content": str}`.
- Constantes exportées : `TOOL_INPUT_CAP = 300`, `TOOL_OUTPUT_CAP = 1000`, `TOTAL_CAP = 30000`.

- [ ] **Step 1: Écrire les tests en échec**

Créer `tests/test_catchup.py` :

```python
"""Tests du rendu du message de rattrapage."""

import json

import pytest

from web.catchup import TOTAL_CAP, build_catchup
from web.database import Message


def _msg(msg_id, type_, content):
    return Message(id=msg_id, conversation_id="c1", type=type_, content=content)


def test_empty_input_yields_empty_catchup():
    assert build_catchup([]) == []


def test_renders_user_and_assistant_turns():
    msgs = [_msg(1, "user", "quelle audience ?"), _msg(2, "assistant", "je regarde")]

    assert build_catchup(msgs) == [
        {"role": "user", "content": "quelle audience ?"},
        {"role": "assistant", "content": "je regarde"},
    ]


def test_renders_tool_use_and_tool_result():
    msgs = [
        _msg(1, "tool_use", json.dumps({"tool": "Read", "input": {"file_path": "/a.md"}})),
        _msg(2, "tool_result", json.dumps({"output": "contenu"})),
    ]
    result = build_catchup(msgs)

    assert result[0]["role"] == "assistant"
    assert "Read" in result[0]["content"] and "/a.md" in result[0]["content"]
    assert "contenu" in result[1]["content"]


@pytest.mark.parametrize("ignored", ["system", "limit"])
def test_drops_noise_types(ignored):
    assert build_catchup([_msg(1, ignored, "bruit")]) == []


@pytest.mark.parametrize(
    "type_, content, cap",
    [
        ("tool_use", json.dumps({"tool": "Bash", "input": {"command": "x" * 5000}}), 300),
        ("tool_result", json.dumps({"output": "y" * 5000}), 1000),
    ],
)
def test_caps_tool_payloads(type_, content, cap):
    rendered = build_catchup([_msg(1, type_, content)])[0]["content"]

    assert len(rendered) < cap + 200
    assert "tronqué" in rendered


def test_caps_total_size_keeping_the_tail():
    msgs = [_msg(i, "assistant", f"bloc {i} " + "z" * 900) for i in range(60)]
    msgs.append(_msg(999, "user", "DERNIER MESSAGE"))
    result = build_catchup(msgs)

    total = sum(len(e["content"]) for e in result)
    assert total <= TOTAL_CAP
    assert "DERNIER MESSAGE" in result[-1]["content"]


def test_tolerates_non_json_tool_content():
    assert build_catchup([_msg(1, "tool_use", "pas du json")])[0]["content"]
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `DATABASE_URL= REDIS_URL= uv run --frozen pytest tests/test_catchup.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'web.catchup'`.

- [ ] **Step 3: Écrire l'implémentation minimale**

Créer `web/catchup.py` :

```python
"""Rendu du message de rattrapage donné à un moteur qui reprend la main."""

import json

TOOL_INPUT_CAP = 300
TOOL_OUTPUT_CAP = 1000
TOTAL_CAP = 30000

_KEPT_TYPES = ("user", "assistant", "tool_use", "tool_result")


def _clip(text: str, cap: int) -> str:
    if len(text) <= cap:
        return text
    return f"{text[:cap]}… [tronqué, {len(text)} caractères au total]"


def _render(msg) -> dict | None:
    if msg.type == "user":
        return {"role": "user", "content": msg.content}
    if msg.type == "assistant":
        return {"role": "assistant", "content": msg.content}

    try:
        payload = json.loads(msg.content)
    except (json.JSONDecodeError, TypeError):
        payload = {}

    if msg.type == "tool_use":
        tool = payload.get("tool") or "outil"
        rendered = _clip(json.dumps(payload.get("input", {}), ensure_ascii=False), TOOL_INPUT_CAP)
        return {"role": "assistant", "content": f"[appel {tool}] {rendered}"}

    output = payload.get("output", msg.content)
    if not isinstance(output, str):
        output = json.dumps(output, ensure_ascii=False)
    return {"role": "assistant", "content": f"[résultat] {_clip(output, TOOL_OUTPUT_CAP)}"}


def build_catchup(messages: list) -> list[dict]:
    """Ce qui s'est passé depuis qu'un moteur a parlé, borné en taille."""
    entries = [rendered for m in messages if m.type in _KEPT_TYPES if (rendered := _render(m))]

    kept: list[dict] = []
    total = 0
    # Why: on garde la fin — le contexte le plus proche du tour à jouer est le plus utile.
    for entry in reversed(entries):
        size = len(entry["content"])
        if total + size > TOTAL_CAP:
            break
        kept.append(entry)
        total += size
    return list(reversed(kept))
```

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

Run: `DATABASE_URL= REDIS_URL= uv run --frozen pytest tests/test_catchup.py -v && make lint`
Expected: PASS, lint propre.

- [ ] **Step 5: Commit**

```bash
git add web/catchup.py tests/test_catchup.py
git commit -m "feat(catchup): render a size-capped catch-up from stored messages"
```

---

### Task 6: `history_for_turn` généralisé, et suppression de la branche `is_resume`

**Zones critiques : `web/runner.py` et `web/agents/cli.py`. À signaler en relecture.**

C'est le cœur du design : une seule fonction décide de ce que le moteur doit rattraper, et le comportement actuel devient son cas dégénéré.

**Files:**
- Modify: `web/runner.py` (`history_for_turn`, `_consumer_loop`)
- Modify: `web/agents/cli.py` (`_run_attempt`, ~l.177-183)
- Test: `tests/test_runner_history.py`

**Interfaces:**
- Consomme : `build_catchup` (tâche 5), `store.get_engine_state` (tâche 4).
- Produit : `history_for_turn(conv_id: str, session_id: str | None, default_history: list[dict], seen_through: int | None = None) -> list[dict]`.

- [ ] **Step 1: Écrire les tests en échec**

Ajouter à `tests/test_runner_history.py` (les tests existants restent et doivent continuer à passer — c'est la non-régression du cas dégénéré) :

```python
def _msg(msg_id, type_, content):
    return Message(id=msg_id, conversation_id="c1", type=type_, content=content)


def test_returns_catchup_when_session_exists_and_something_happened(mocker):
    mocker.patch.object(runner.session_sync, "get_session_path", return_value=mocker.Mock(exists=lambda: True))
    msgs = [
        _msg(1, "user", "vu"),
        _msg(2, "assistant", "déjà vu"),
        _msg(3, "assistant", "nouveau"),
        _msg(4, "tool_use", '{"tool": "Read", "input": {"file_path": "/a"}}'),
    ]
    mocker.patch.object(runner.store, "get_conversation", return_value=_conv(msgs))

    result = runner.history_for_turn("c1", "sess-1", [], seen_through=2)

    assert [e["content"] for e in result] == ["nouveau", "[appel Read] {\"file_path\": \"/a\"}"]


def test_returns_empty_catchup_when_nothing_happened_since(mocker):
    mocker.patch.object(runner.session_sync, "get_session_path", return_value=mocker.Mock(exists=lambda: True))
    msgs = [_msg(1, "user", "vu"), _msg(2, "assistant", "déjà vu")]
    mocker.patch.object(runner.store, "get_conversation", return_value=_conv(msgs))

    assert runner.history_for_turn("c1", "sess-1", [], seen_through=2) == []


def test_session_missing_still_wins_over_catchup(mocker):
    mocker.patch.object(runner.session_sync, "get_session_path", return_value=mocker.Mock(exists=lambda: False))
    msgs = [_msg(1, "user", "a"), _msg(2, "assistant", "b"), _msg(3, "user", "c")]
    mocker.patch.object(runner.store, "get_conversation", return_value=_conv(msgs))

    result = runner.history_for_turn("c1", "sess-1", [], seen_through=2)

    assert result == [{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}]
```

Ajouter à `tests/test_agents_cli.py` :

```python
@pytest.mark.parametrize(
    "history, expected",
    [
        ([], "ma question"),
        ([{"role": "assistant", "content": "rattrapage"}], "Assistant: rattrapage\n\nUser: ma question"),
    ],
)
def test_resume_prompt_includes_catchup_when_present(history, expected):
    from web.agents.cli import CLIBackend

    assert CLIBackend()._build_prompt("ma question", history) == expected
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `DATABASE_URL= REDIS_URL= uv run --frozen pytest tests/test_runner_history.py tests/test_agents_cli.py -v`
Expected: FAIL — `history_for_turn()` ne prend pas `seen_through`.

- [ ] **Step 3: Généraliser `history_for_turn`**

Remplacer la fonction dans `web/runner.py` :

```python
def history_for_turn(
    conv_id: str,
    session_id: str | None,
    default_history: list[dict],
    seen_through: int | None = None,
) -> list[dict]:
    """Ce que le moteur doit rattraper : rien, l'intermède de l'autre moteur, ou tout le transcript."""
    session_present = bool(session_id) and session_sync.get_session_path(session_id).exists()

    if not session_id:
        return default_history

    if session_present and seen_through is None:
        return default_history

    conv = store.get_conversation(conv_id, include_messages=True)
    if not conv:
        return default_history

    if session_present:
        return build_catchup([m for m in conv.messages if m.id and m.id > seen_through])

    logger.warning("Session file %s missing for %s — falling back to full history", session_id, conv_id)
    sentry_sdk.capture_message(
        f"Resume unavailable for conversation {conv_id}; using history fallback", level="warning"
    )
    msgs = [m for m in conv.messages if m.type in ("user", "assistant")]
    if msgs and msgs[-1].type == "user":
        msgs = msgs[:-1]
    return [{"role": m.type, "content": m.content} for m in msgs]
```

Ajouter `from web.catchup import build_catchup` aux imports de `web/runner.py`.

Dans `_consumer_loop`, le repère vient de l'état du moteur choisi. Le choix du moteur y remonte donc depuis `_run_agent` :

```python
                backend_name = await pick_backend()
                state = await asyncio.to_thread(store.get_engine_state, conv_id, backend_name)
                sid = state["session_id"] or payload.get("session_id")
                if sid:
                    await asyncio.to_thread(session_sync.download_session, sid)
                history = history_for_turn(conv_id, sid, payload["history"], state["seen_through"])
```

et `_run_agent` reçoit `backend_name` en paramètre au lieu de rappeler `pick_backend()` :

```python
                task = asyncio.create_task(
                    self._run_agent(
                        conv_id,
                        payload["prompt"],
                        history,
                        payload.get("user_email"),
                        trace_headers,
                        sid,
                        backend_name,
                    )
                )
```

Dans `_run_agent`, remplacer le `backend_name = await pick_backend()` de la tâche 3 par le paramètre reçu (signature : `..., session_id: str | None = None, backend_name: str | None = None`, et `backend = get_agent(backend_name)`).

**Ordre des messages** : `get_conversation` trie par `timestamp`. Deux messages d'un même tour peuvent partager un horodatage — le filtre `m.id > seen_through` reste correct, mais ajouter `sorted(..., key=lambda m: m.id)` avant `build_catchup` garantit un rendu déterministe.

- [ ] **Step 4: Supprimer la branche `is_resume` dans `cli.py`**

Dans `web/agents/cli.py`, `_run_attempt`, remplacer :

```python
        is_resume = session_id is not None and session_sync.get_session_path(session_id).exists()

        if is_resume:
            prompt = message
        else:
            prompt = self._build_prompt(message, history)
        outcome["prompt"] = prompt
```

par :

```python
        is_resume = session_id is not None and session_sync.get_session_path(session_id).exists()
        # Why: _build_prompt rend le message seul quand l'historique est vide — le cas « reprise
        # sans rattrapage » est donc déjà couvert, sans branche dédiée.
        prompt = self._build_prompt(message, history)
        outcome["prompt"] = prompt
```

`is_resume` reste utilisé plus bas pour `--resume` / `--session-id` et pour le span.

- [ ] **Step 5: Lancer les tests pour vérifier qu'ils passent**

Run: `DATABASE_URL= REDIS_URL= uv run --frozen pytest tests/test_runner_history.py tests/test_agents_cli.py tests/test_runner.py -v`
Expected: PASS, y compris les tests de non-régression existants.

- [ ] **Step 6: Vérification complète et commit**

Run: `make lint && make test`
Expected: lint propre, suite unit verte.

```bash
git add web/runner.py web/agents/cli.py tests/test_runner_history.py tests/test_agents_cli.py
git commit -m "feat(runner): feed each engine a catch-up instead of an empty history"
```

---

### Task 7: Avancer le repère, uniquement sur un tour complet

**Zone critique : `web/runner.py`. À signaler en relecture.**

C'est le point de vigilance nº 2 : une limite atteinte en plein stream ne doit pas figer un repère corrompu.

**Files:**
- Modify: `web/runner.py` (`_run_agent`)
- Test: `tests/test_runner_marker.py` (créer)

**Interfaces:**
- Consomme : `store.set_engine_state` (tâche 4).
- Produit : rien de nouveau. `_run_agent` écrit `session_id` et `seen_through` du moteur utilisé à la fin d'un tour dont `agent_status == "ok"`.

- [ ] **Step 1: Écrire les tests en échec**

Créer `tests/test_runner_marker.py` :

```python
"""Le repère par moteur n'avance que sur un tour complet."""

import asyncio

import fakeredis.aioredis
import pytest

from web import runner
from web.agents.base import AgentMessage
from web.runner import TaskRunner


def _stream(*msgs):
    async def gen(**kwargs):
        for m in msgs:
            yield m

    return gen


@pytest.fixture
def fake_redis():
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


def _make(mocker, fake_redis, *events):
    mocker.patch("web.runner.config.AGENT_BACKEND", "cli")
    mocker.patch("web.runner.config.AGENT_FALLBACK_BACKEND", "")
    mocker.patch("web.runner.get_redis", return_value=fake_redis)
    mocker.patch("web.runner.session_sync")
    mocker.patch("web.runner._check_failure")
    mocker.patch.object(runner.store, "update_conversation")
    mocker.patch.object(runner.store, "get_conversation", return_value=None)
    mocker.patch.object(runner.store, "add_message", return_value=mocker.Mock(id=57))
    backend = mocker.MagicMock()
    backend.send_message = _stream(*events)
    mocker.patch("web.runner.get_agent", return_value=backend)
    return TaskRunner()


def test_marker_advances_after_a_complete_turn(mocker, fake_redis):
    set_state = mocker.patch.object(runner.store, "set_engine_state")
    r = _make(mocker, fake_redis, AgentMessage(type="assistant", content="fini"))

    asyncio.run(r._run_agent("c1", "p", [], None, None, "sess-1", "cli"))

    set_state.assert_called_once_with("c1", "cli", session_id="sess-1", seen_through=57)


def test_marker_does_not_advance_when_the_turn_hits_a_limit(mocker, fake_redis):
    set_state = mocker.patch.object(runner.store, "set_engine_state")
    limit = AgentMessage(type="limit", content="limite", raw={"reset": None})
    r = _make(mocker, fake_redis, limit)

    asyncio.run(r._run_agent("c1", "p", [], None, None, "sess-1", "cli"))

    set_state.assert_not_called()
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `DATABASE_URL= REDIS_URL= uv run --frozen pytest tests/test_runner_marker.py -v`
Expected: FAIL — `set_engine_state` n'est jamais appelé.

- [ ] **Step 3: Écrire l'implémentation minimale**

Dans `_run_agent`, suivre l'identifiant du dernier message écrit. Là où `store.add_message` est appelé (branches `assistant`, `tool_use`/`tool_result`), capturer le retour dans un `last_message_id` local :

```python
        last_message_id: int | None = None
```

Dans la branche `assistant`, après `msg = store.add_message(...)` : `last_message_id = msg.id if msg else last_message_id`.
Dans la branche outils, remplacer `store.add_message(conversation_id, event.type, content)` par :

```python
                        stored = store.add_message(conversation_id, event.type, content)
                        if stored:
                            last_message_id = stored.id
```

Puis, dans le `finally`, à l'intérieur du bloc `if slot is my_task or slot is None:` et **avant** `store.update_conversation(...)` :

```python
                    if agent_status == "ok" and last_message_id is not None:
                        store.set_engine_state(
                            conversation_id,
                            backend_name,
                            session_id=session_id,
                            seen_through=last_message_id,
                        )
```

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

Run: `DATABASE_URL= REDIS_URL= uv run --frozen pytest tests/test_runner_marker.py tests/test_runner.py -v && make lint`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/runner.py tests/test_runner_marker.py
git commit -m "feat(runner): advance the per-engine marker only on a completed turn"
```

---

### Task 8: Rejouer le tour perdu sur le moteur de secours

**Zone critique : `web/runner.py`. À signaler en relecture.**

**Files:**
- Modify: `web/runner.py` (`_run_agent`)
- Test: `tests/test_runner_reroute.py` (créer)

**Interfaces:**
- Consomme : `mark_backend_limited`, `pick_backend` (tâche 3), `history_for_turn` (tâche 6).
- Produit : rien de nouveau. `_run_agent` relance une fois le tour sur `config.AGENT_FALLBACK_BACKEND`.

- [ ] **Step 1: Écrire les tests en échec**

Créer `tests/test_runner_reroute.py` :

```python
"""Un tour coupé par la limite d'usage est rejoué une fois sur le moteur de secours."""

import asyncio

import fakeredis.aioredis
import pytest

from web import runner
from web.agents.base import AgentMessage
from web.runner import TaskRunner

LIMIT = AgentMessage(type="limit", content="limite", raw={"reset": "2026-09-08T20:00:00+00:00"})


def _stream(*msgs):
    async def gen(**kwargs):
        for m in msgs:
            yield m

    return gen


def _backend(mocker, *events):
    b = mocker.MagicMock()
    b.send_message = _stream(*events)
    return b


@pytest.fixture
def fake_redis():
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


@pytest.fixture(autouse=True)
def _isolate(mocker, fake_redis):
    mocker.patch("web.runner.config.AGENT_BACKEND", "cli")
    mocker.patch("web.runner.config.AGENT_FALLBACK_BACKEND", "cli-ollama")
    mocker.patch("web.runner.get_redis", return_value=fake_redis)
    mocker.patch("web.runner.session_sync")
    mocker.patch("web.runner._check_failure")
    mocker.patch("web.runner.history_for_turn", return_value=[])
    mocker.patch.object(runner.store, "update_conversation")
    mocker.patch.object(runner.store, "get_conversation", return_value=None)
    mocker.patch.object(runner.store, "add_message", return_value=mocker.Mock(id=1))
    mocker.patch.object(runner.store, "set_engine_state")
    mocker.patch.object(runner.store, "get_engine_state", return_value={"session_id": "s2", "seen_through": 3})


def test_limit_reroutes_once_to_the_fallback(mocker):
    marked = mocker.patch("web.runner.mark_backend_limited", new=mocker.AsyncMock())
    agents = mocker.patch(
        "web.runner.get_agent",
        side_effect=[
            _backend(mocker, LIMIT),
            _backend(mocker, AgentMessage(type="assistant", content="repris")),
        ],
    )

    asyncio.run(TaskRunner()._run_agent("c1", "p", [], None, None, "s1", "cli"))

    marked.assert_awaited_once_with("cli", "2026-09-08T20:00:00+00:00")
    assert [c.args[0] for c in agents.call_args_list] == ["cli", "cli-ollama"]


def test_no_second_reroute_when_the_fallback_also_hits_a_limit(mocker):
    mocker.patch("web.runner.mark_backend_limited", new=mocker.AsyncMock())
    agents = mocker.patch("web.runner.get_agent", return_value=_backend(mocker, LIMIT))

    asyncio.run(TaskRunner()._run_agent("c1", "p", [], None, None, "s2", "cli-ollama"))

    assert agents.call_count == 1


def test_no_reroute_without_a_fallback_configured(mocker):
    mocker.patch("web.runner.config.AGENT_FALLBACK_BACKEND", "")
    mocker.patch("web.runner.mark_backend_limited", new=mocker.AsyncMock())
    agents = mocker.patch("web.runner.get_agent", return_value=_backend(mocker, LIMIT))

    asyncio.run(TaskRunner()._run_agent("c1", "p", [], None, None, "s1", "cli"))

    assert agents.call_count == 1


def test_limit_message_is_written_when_no_reroute_happens(mocker):
    mocker.patch("web.runner.config.AGENT_FALLBACK_BACKEND", "")
    mocker.patch("web.runner.get_agent", return_value=_backend(mocker, LIMIT))

    asyncio.run(TaskRunner()._run_agent("c1", "p", [], None, None, "s1", "cli"))

    assert any(c.args[1] == "limit" for c in runner.store.add_message.call_args_list)
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `DATABASE_URL= REDIS_URL= uv run --frozen pytest tests/test_runner_reroute.py -v`
Expected: FAIL — un seul moteur est sollicité, aucun rejeu.

- [ ] **Step 3: Écrire l'implémentation minimale**

**L'extraction, précisément.** Renommer la méthode `_run_agent` existante en `_stream_turn` **sans toucher à son corps**, sauf les quatre modifications listées aux points a) à d) ci-dessous. Sa signature devient :

```python
    async def _stream_turn(
        self,
        conversation_id: str,
        prompt: str,
        history: list[dict],
        user_email: str | None,
        trace_headers: dict | None,
        session_id: str | None,
        backend_name: str,
        release: bool,
    ) -> str | None:
```

a) Déclarer `limit_reset: str | None = None` à côté des autres locales, en tête de méthode.
b) Remplacer la branche `elif event.type == "limit":` par le bloc donné plus bas.
c) Dans le `finally`, encadrer la libération de la conversation par `release` : `if release and (slot is my_task or slot is None):`. Les autres nettoyages (`_close_tool_log`, `tool_spans.close_all`, `reset_conversation_id`, `cancel_task.cancel`) restent inconditionnels.

**Attention à l'écriture du repère de la tâche 7.** Elle vit aujourd'hui dans ce bloc ; l'y laisser sous `release` ferait qu'un tour réussi sur la première passe n'avancerait plus son repère, puisque `release` y vaut `False` dès qu'un rejeu est possible. La sortir du bloc `release` et la conditionner à sa seule règle métier :

```python
                if agent_status == "ok" and last_message_id is not None:
                    store.set_engine_state(
                        conversation_id,
                        backend_name,
                        session_id=session_id,
                        seen_through=last_message_id,
                    )
                if release and (slot is my_task or slot is None):
                    store.update_conversation(conversation_id, needs_response=False)
                    ...
```
d) Terminer la méthode par `return limit_reset`, après le bloc `with`.

Puis écrire la nouvelle `_run_agent`, qui devient une simple enveloppe de routage :

```python
    async def _run_agent(
        self,
        conversation_id: str,
        prompt: str,
        history: list[dict],
        user_email: str | None,
        trace_headers: dict | None = None,
        session_id: str | None = None,
        backend_name: str | None = None,
    ):
        backend_name = backend_name or config.AGENT_BACKEND
        fallback = config.AGENT_FALLBACK_BACKEND
        may_reroute = bool(fallback) and backend_name != fallback

        limit_reset = await self._stream_turn(
            conversation_id,
            prompt,
            history,
            user_email,
            trace_headers,
            session_id,
            backend_name,
            release=not may_reroute,
        )

        if limit_reset is None or not may_reroute:
            return

        await mark_backend_limited(backend_name, limit_reset)
        logger.info("Usage limit on %s for %s — replaying the turn on %s", backend_name, conversation_id, fallback)
        state = await asyncio.to_thread(store.get_engine_state, conversation_id, fallback)
        fallback_sid = state["session_id"] or str(uuid.uuid4())
        if state["session_id"]:
            await asyncio.to_thread(session_sync.download_session, fallback_sid)
        fallback_history = await asyncio.to_thread(
            history_for_turn, conversation_id, fallback_sid, history, state["seen_through"]
        )
        await self._stream_turn(
            conversation_id,
            prompt,
            fallback_history,
            user_email,
            trace_headers,
            fallback_sid,
            fallback,
            release=True,
        )
```

**Le piège du `release`.** Quand un rejeu est possible, la première tentative ne doit **pas** libérer la conversation : `update_conversation(needs_response=False)`, `notify_done` et la suppression de la clé Redis fermeraient le flux SSE avant que le moteur de secours ait répondu. D'où `release=not may_reroute` sur la première passe et `release=True` sur la seconde. Si aucun rejeu n'est possible, la première passe libère comme aujourd'hui.

**Le message de limite.** Il ne doit s'afficher que si personne ne reprend la main. Remplacer la branche `elif event.type == "limit":` par :

```python
                    elif event.type == "limit":
                        limit_reset = event.raw.get("reset")
                        agent_status = "error"
                        if release:
                            store.add_message(conversation_id, "limit", str(event.content))
                            await self.notify(conversation_id)
                            await self._alert_usage_limit_once(limit_reset)
```

`release` vaut `False` exactement quand un rejeu va suivre : le même drapeau gouverne les deux comportements, il n'y a donc pas deux conditions à garder synchronisées.

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

Run: `DATABASE_URL= REDIS_URL= uv run --frozen pytest tests/test_runner_reroute.py tests/test_runner.py tests/test_runner_marker.py -v`
Expected: PASS.

- [ ] **Step 5: Vérification complète et commit**

Run: `make lint && make test`
Expected: lint propre, suite unit verte.

```bash
git add web/runner.py tests/test_runner_reroute.py
git commit -m "feat(runner): replay a usage-limited turn on the fallback engine"
```

---

### Task 9: Attribuer l'usage au moteur réellement utilisé

`config.AGENT_BACKEND` est aujourd'hui lu directement pour les spans, le tag Sentry et `insert_usage_event`. Sans ce correctif, tous les tours joués par le secours sont comptabilisés sur le moteur principal.

**Files:**
- Modify: `web/runner.py` (`_stream_turn`, `_record_usage`, `_record_thinking_tail`)
- Test: `tests/test_runner_usage.py` (créer)

**Interfaces:**
- Consomme : `backend_name` (tâche 8).
- Produit : `_record_usage(conversation_id, raw_event, run_usage, backend)` et `_record_thinking_tail(conversation_id, result_usage, run_usage, backend)` prennent le moteur en paramètre.

- [ ] **Step 1: Écrire le test en échec**

Créer `tests/test_runner_usage.py` :

```python
"""L'usage est attribué au moteur qui a réellement joué le tour."""

from web import runner


def test_usage_is_attributed_to_the_running_backend(mocker):
    mocker.patch.object(runner.config, "AGENT_BACKEND", "cli")
    insert = mocker.patch.object(runner.store, "insert_usage_event")
    raw = {"message": {"id": "m1", "model": "glm-5.2", "usage": {"output_tokens": 12}}}

    runner._record_usage("c1", raw, runner.RunUsage(), "cli-ollama")

    assert insert.call_args.kwargs["backend"] == "cli-ollama"
```

- [ ] **Step 2: Lancer le test pour vérifier qu'il échoue**

Run: `DATABASE_URL= REDIS_URL= uv run --frozen pytest tests/test_runner_usage.py -v`
Expected: FAIL — `_record_usage()` ne prend que trois arguments.

- [ ] **Step 3: Écrire l'implémentation minimale**

Ajouter le paramètre `backend: str` à `_record_usage` et `_record_thinking_tail`, et y remplacer `backend=config.AGENT_BACKEND` par `backend=backend`. Répercuter aux deux appels dans `_stream_turn` : `_record_usage(conversation_id, event.raw, run_usage, backend_name)` et `_record_thinking_tail(conversation_id, event.raw["usage"], run_usage, backend_name)`.

Dans `_stream_turn`, remplacer aussi l'attribut de span et le tag Sentry :

```python
            attributes={"conversation_id": conversation_id, "agent_backend": backend_name},
```
```python
            sentry_sdk.set_tag("agent_backend", backend_name)
```

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

Run: `DATABASE_URL= REDIS_URL= uv run --frozen pytest tests/test_runner_usage.py tests/test_runner.py -v`
Expected: PASS. Les tests existants qui patchent `web.runner.config.AGENT_BACKEND` continuent de passer, le moteur par défaut restant `config.AGENT_BACKEND`.

- [ ] **Step 5: Vérification finale et commit**

Run: `make lint && make test && uv run --frozen alembic check`
Expected: tout vert.

```bash
git add web/runner.py tests/test_runner_usage.py
git commit -m "feat(runner): attribute usage events to the backend that ran the turn"
```

---

### Task 10: Validation bout en bout contre Ollama Cloud

Les points que l'exploration a laissés ouverts : l'enchaînement long, `--resume` sur une session écrite par le moteur de secours, et le choix du modèle. Aucun de ces tests ne tourne en CI.

**Files:**
- Test: `tests/test_fallback_external.py` (créer)

**Interfaces:**
- Consomme : tout ce qui précède.
- Produit : rien de nouveau.

- [ ] **Step 1: Écrire le test externe**

Créer `tests/test_fallback_external.py` :

```python
"""Parcours réel contre Ollama Cloud. Requiert OLLAMA_API_KEY. Aucune CI ne l'exécute."""

import asyncio
import uuid

import pytest

from web import config, session_sync
from web.agents import get_agent

pytestmark = pytest.mark.external


def _texts(msgs):
    return " ".join(str(m.content) for m in msgs if m.type == "assistant")


@pytest.mark.skipif(not config.OLLAMA_API_KEY, reason="OLLAMA_API_KEY absent")
def test_fallback_calls_tools_then_resumes(tmp_path):
    target = tmp_path / "secret.txt"
    target.write_text("Le mot secret est ANANAS-4712.\n")
    backend = get_agent("cli-ollama")
    conv_id, session_id = str(uuid.uuid4()), str(uuid.uuid4())

    async def _collect(prompt):
        return [m async for m in backend.send_message(conv_id, prompt, [], session_id=session_id)]

    first = asyncio.run(_collect(f"Lis {target} et dis-moi le mot secret."))
    assert any(m.type == "tool_use" for m in first)
    assert "ANANAS-4712" in _texts(first)

    assert session_sync.get_session_path(session_id).exists()

    second = asyncio.run(_collect("Répète le mot secret, sans relire le fichier."))
    assert "ANANAS-4712" in _texts(second)
```

- [ ] **Step 2: Vérifier que le test est bien exclu du couloir unit**

Run: `DATABASE_URL= REDIS_URL= uv run --frozen pytest -m "not integration and not e2e and not external" --collect-only -q | tail -3`
Expected: `test_fallback_external.py` n'apparaît pas.

- [ ] **Step 3: Lancer le test réel**

Run: `OLLAMA_API_KEY=<clé> AGENT_FALLBACK_BACKEND=cli-ollama uv run --frozen pytest tests/test_fallback_external.py -v -m external`
Expected: PASS. En cas d'échec sur le second appel, `--resume` ne fonctionne pas avec ce modèle — le consigner dans la spec et essayer `glm-5.3` puis `kimi-k2.7-code`.

- [ ] **Step 4: Comparer les modèles candidats**

Run: `uv run --frozen python evals/run_eval.py --backends cli ollama`
Expected: un tableau comparatif. Retenir le modèle qui tient sur des questions analytiques en français et fixer `OLLAMA_MODEL` en conséquence dans `.env.example`.

- [ ] **Step 5: Commit**

```bash
git add tests/test_fallback_external.py
git commit -m "test(fallback): add an external end-to-end check against Ollama Cloud"
```

---

## Notes de relecture

**Ce chantier touche des zones critiques et nécessite une relecture humaine** : `web/models.py` (tâche 4), `alembic/` (tâche 4), `web/runner.py` (tâches 3, 6, 7, 8, 9), `web/agents/cli.py` (tâche 6).

**Réversibilité.** `AGENT_FALLBACK_BACKEND` vide éteint le routage, le rejeu et le rattrapage : `pick_backend` rend le moteur principal, `history_for_turn` reçoit un `seen_through` à `None` pour une session existante et rend `default_history`, soit exactement le comportement actuel. La colonne `engine_state` peut rester en place sans être lue.

**Ordre.** La tâche 1 est indépendante et peut être mergée seule. Les tâches 2 à 4 sont indépendantes entre elles. La tâche 6 dépend des tâches 4 et 5, la 7 de la 4, la 8 des tâches 3 et 6, la 9 de la 8.

**Non couvert par ce plan** : le mode dégradé quand le moteur de secours est injoignable au niveau réseau se contente du comportement d'échec existant de `CLIBackend` (message d'erreur), sans nouvelle logique — conformément à la règle « pas de gestion d'erreur pour des cas impossibles » appliquée avec parcimonie ici, puisque le cas est possible mais déjà couvert.
