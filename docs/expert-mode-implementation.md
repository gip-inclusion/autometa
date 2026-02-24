# Expert Mode: Auto-create Gitea Repo + Webhook Auto-redeploy

**Date**: 2026-02-24
**Branch**: `mode_expert`
**Status**: Implemented, iteratively debugged through 4 rebuild cycles

---

## Goal

Automate the expert mode pipeline: when a user clicks "Nouvelle app", a Gitea repo should be created automatically, cloned locally so the agent can commit/push, and on first Coolify deploy a webhook should be set up for auto-redeploy on push.

---

## What was implemented

### Feature 1: Auto-create Gitea repo on project creation

**Files modified**: `web/routes/expert.py`, `skills/project_git/scripts/git_ops.py`

Two helper functions added to `expert.py`:

- **`_authenticated_clone_url(repo_path)`** — builds `http://<token>@host:port/org/repo.git` using `GITEA_URL` + `GITEA_API_TOKEN`. Required because the Gitea API returns `http://localhost:3300/...` as `clone_url`, which is wrong inside Docker (should be `host.docker.internal:3300`) and has no auth (so `git push` would fail).

- **`_try_create_gitea_repo(project)`** — called after `store.create_project()` in both `expert_new()` (HTML route) and `api_create_project()` (API route). It:
  1. Creates a Gitea repo via `GiteaClient.create_repo()`
  2. Clones it into `data/projects/<uuid>/` using the authenticated URL
  3. Configures `git user.email` and `git user.name` in the local repo
  4. Updates the project record with `gitea_repo_id`, `gitea_url`, `status="active"`
  5. Wrapped in try/except — failure does NOT block project creation

The `git_ops.py` `cmd_init` was also refactored to:
- Work when `gitea_repo_id` already exists (clone locally if `.git` is missing)
- Use `_authenticated_clone_url()` instead of the bare Gitea `clone_url`
- Skip commit if nothing staged (avoids error on re-init)

### Feature 2: Gitea webhook → Coolify auto-redeploy

**Files modified**: `lib/gitea.py`, `lib/coolify.py`, `web/routes/expert.py`, `web/config.py`, `.env.example`

- **`GiteaClient.create_webhook(owner, repo, url, secret, events)`** — POSTs to `/api/v1/repos/{owner}/{repo}/hooks` with type `"gitea"`, JSON content type, configurable events (defaults to `["push"]`).

- **`CoolifyClient.get_webhook_secret(app_uuid)`** — reads `manual_webhook_secret_gitea` from the Coolify app config.

- **`CoolifyClient.set_webhook_secret(app_uuid, secret)`** — PATCHes the Coolify app to set the secret.

- **`_setup_gitea_webhook(project, app_uuid, coolify)`** in `expert.py` — called after first Coolify app creation + first deploy. It:
  1. Gets or generates a webhook secret on the Coolify app
  2. Builds webhook URL: `{COOLIFY_INTERNAL_URL}/webhooks/source/gitea/events/manual`
  3. Extracts owner/repo from `project.gitea_url`
  4. Creates the Gitea webhook
  5. Non-blocking (logs errors, never raises)

- **`COOLIFY_INTERNAL_URL`** config var (defaults to `http://coolify:8080`) — Gitea sends webhooks from inside Docker, needs container DNS name + internal port.

### Feature 3: Agent can commit and push (ALLOWED_TOOLS fix)

**File modified**: `web/config.py`

Added `Bash(git:*)` to the default `ALLOWED_TOOLS` whitelist. Without this, the agent could write files via `Write`/`Edit` but was blocked from running `git add`, `git commit`, `git push`.

---

## Bugs found and fixed along the way

### Bug 1: Permission denied on `/app/data/projects/`

**Error**: `[Errno 13] Permission denied: '/app/data/projects/<uuid>'`

**Root cause**: The Dockerfile created `/app/data/uploads` and `/app/data/modified` but not `/app/data/projects`. The host `data/projects/` directory was owned by the host user with `drwxr-xr-x` permissions — the container user (UID 1004, `matometa`) had no write access.

**Fix**:
- `Dockerfile`: added `/app/data/projects` to the `mkdir` line
- Host: `sudo chown -R 1004:1004 data/projects` to match container UID

### Bug 2: SSE crash on multi-part tool results

**Error**: `expected string or bytes-like object, got 'list'` in `lib/api_signals.py:72`

**Root cause**: In `web/routes/conversations.py`, when `event.content` is a dict with `'output'` key, `event.content['output']` can be a **list** (multi-part tool result from Claude CLI). That list was passed directly to `parse_api_signals()` which calls `regex.finditer()` on it.

**Fix**: Added a type guard after extracting `raw_content`:
```python
if not isinstance(raw_content, str):
    raw_content = str(raw_content)
```

### Bug 3: Coolify "Cannot connect to real-time service"

**Error**: Warning popup in Coolify UI

**Root cause**: `PUSHER_HOST=coolify-realtime` in `docker-compose.expert.yml` is a Docker-internal DNS name. Coolify's Laravel broadcasting config uses a separate `PUSHER_BACKEND_HOST` (defaults to `coolify-realtime`) for the PHP backend, but `PUSHER_HOST` is rendered into the browser's Echo JS config as `wsHost`. The browser can't resolve `coolify-realtime`.

**Fix**: Changed `PUSHER_HOST=localhost` in `docker-compose.expert.yml`. The PHP backend still uses `PUSHER_BACKEND_HOST` (defaults to `coolify-realtime`), while the browser connects to `localhost:6001`.

### Bug 4: No Gitea repo created (container not rebuilt)

**Symptom**: Clicking "Nouvelle app" created a project but no Gitea repo appeared.

**Root cause**: The Docker container was running an old image (built before the `_try_create_gitea_repo` code was added). `docker compose up -d` does NOT rebuild — it reuses the existing image.

**Fix**: `docker compose up --build -d matometa` to force a rebuild. This happened multiple times during the session.

### Bug 5: Repo created but not cloned locally

**Symptom**: Gitea repo existed but `data/projects/<uuid>/` had no `.git` directory. Agent wrote files but couldn't push.

**Root cause**: The initial `_try_create_gitea_repo` implementation created the Gitea repo and updated the DB, but didn't clone it into the project working directory. The `git_ops init` skill would skip because `project.gitea_repo_id` was already set.

**Fix**: Added `git clone` + `git config` to `_try_create_gitea_repo`. Also refactored `git_ops init` to handle the case where the repo exists but `.git` doesn't.

### Bug 6: Clone URL wrong inside Docker + no auth

**Symptom**: Even after cloning, `git push` would fail.

**Root cause**: Gitea's API returns `clone_url: http://localhost:3300/apps/slug.git` — wrong hostname inside Docker (should be `host.docker.internal:3300`) and no authentication token embedded.

**Fix**: Created `_authenticated_clone_url()` that builds the URL from `config.GITEA_URL` (correct for the environment) and embeds the API token: `http://<token>@host.docker.internal:3300/apps/slug.git`.

### Bug 7: Agent can't run git commands

**Symptom**: Agent writes files but never commits or pushes.

**Root cause**: `ALLOWED_TOOLS` in `web/config.py` whitelisted `Read, Write, Edit, Glob, Grep` and specific `Bash(curl:...)`, `Bash(python:...)` patterns, but had **no `Bash(git:*)`**. The agent was blocked from running any git commands.

**Fix**: Added `Bash(git:*)` to the default `ALLOWED_TOOLS`.

---

## Files modified (complete list)

| File | Changes |
|------|---------|
| `web/routes/expert.py` | Added `_authenticated_clone_url()`, `_try_create_gitea_repo()`, `_setup_gitea_webhook()` helpers; wired into `expert_new()`, `api_create_project()`, `api_deploy_project()` |
| `lib/gitea.py` | Added `create_webhook()` method |
| `lib/coolify.py` | Added `get_webhook_secret()`, `set_webhook_secret()` methods |
| `web/config.py` | Added `COOLIFY_INTERNAL_URL` config; added `Bash(git:*)` to `ALLOWED_TOOLS` |
| `.env.example` | Documented `COOLIFY_INTERNAL_URL` |
| `skills/project_git/scripts/git_ops.py` | Refactored `cmd_init` to use authenticated URLs, handle pre-existing repos, clone if `.git` missing |
| `web/routes/conversations.py` | Fixed multi-part tool result crash in SSE streaming |
| `Dockerfile` | Added `/app/data/projects` to `mkdir` line |
| `docker-compose.expert.yml` | Changed `PUSHER_HOST=localhost` (was `coolify-realtime`) |

---

## What remains untested / potential issues

1. **Webhook end-to-end**: The webhook setup code is written but hasn't been tested with an actual Coolify deploy + push cycle. The HMAC-SHA256 signing and Coolify's webhook matching logic need live verification.

2. **Token in git remote URL**: The Gitea API token is embedded in the clone URL stored in `.git/config`. This is standard for service accounts but means anyone with access to the project directory can read the token. Acceptable given the container security boundary.

3. **Concurrent project creation**: If two projects are created simultaneously with the same slug, the Gitea repo creation could race. The DB has a unique slug constraint, but Gitea doesn't — a duplicate repo name would fail at the Gitea API level (caught by try/except, non-blocking).

4. **Agent doesn't auto-push**: The agent has `Bash(git:*)` permission now, but the system prompt only says "Commit and push when ready." The agent may or may not do this autonomously — it depends on the model's interpretation. A more explicit instruction or an auto-push hook after each conversation could help.

5. **Existing projects without `.git`**: Projects created before these changes have files in `data/projects/<uuid>/` but no `.git` directory. The `git_ops init` command now handles this case, but the agent needs to be told to run it.
