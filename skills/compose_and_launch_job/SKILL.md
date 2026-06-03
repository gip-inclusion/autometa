---
name: compose_and_launch_job
description: Compose a domain-loaded system prompt and launch an autometa-jobs run from a user's natural-language intent. Use when the user wants an autonomous/long-running analysis (minutes to hours) that is too big or too slow for the interactive chat — e.g. "run a job analyzing all Dora services".
---

# Compose & Launch a Job

You compose the job's system prompt; **the user never writes it**. An autometa-jobs worker is a blank-slate Claude container on Scaleway: it has **no PG access, no `knowledge/`, no `CLAUDE.md`, none of Autometa's domain context**, and it cannot read any of that at runtime. So you — who *do* have the domain knowledge — must distill the relevant context and bake it, the data, and the task into one **self-contained prompt**.

## When to use

The user asks for work that is autonomous and long (too big/slow for the interactive runner): "go analyze all Dora services and write a report", "review every SIAE in region X", a scheduled weekly brief. For quick questions, just answer in chat — don't launch a job.

## Recipe

1. **Clarify** the task and the expected output (a report? a table? a recommendation?). Ask only what you can't infer.

2. **Gather the relevant domain knowledge.** Read the `knowledge/` files that matter for this task (e.g. `knowledge/sites/dora.md`, the IAE business context, the data schema). **Curate, don't dump** — select only what the job needs. The worker has none of it.

3. **Prepare the data** (if the job analyzes a dataset). Use the **`publish_dataset`** skill to export the query result(s) to S3 and get a presigned URL + schema. For relational data, use its multi-table mode (`--tables`) so the worker can JOIN.

4. **Compose a self-contained system prompt.** It must carry everything the worker lacks:
   - **Role + domain context** — distilled IAE / site / Dora background relevant to the task (what the entities and columns mean, how to interpret them).
   - **Data access** — e.g. `Download the dataset: curl -sL '<presigned-url>' -o data.sqlite`. State the format, table names, and columns.
   - **The task** — concrete steps and the question to answer.
   - **Output** — what the final artifact should be (the worker's last message becomes the artifact).
   - **Environment note** — the sandbox has `Bash`, `python3` (stdlib `sqlite3`, plus `numpy`/`pandas`), `curl`, `git`; no Autometa APIs.

   Write the prompt to a file (avoids shell-escaping issues).

5. **Launch.** Run:

   ```bash
   .venv/bin/python skills/compose_and_launch_job/scripts/launch_job.py \
       --name dora-services-2026-06 \
       --system-prompt-file /tmp/job_prompt.md \
       --max-turns 40 \
       --allowed-tools "Bash,Read,WebFetch"
   ```

   Prints `{ "pipeline_id", "run_id", "status", "run_url" }`. The `--name` must be **globally unique** (include a date/slug); if it collides the orchestrator errors — retry with another name.

6. **Hand back the `run_url`** to the user so they can watch it on `/jobs/runs/{run_id}` (status, live event stream, summary, artifact). Tell them it runs autonomously; they don't need to stay.

## Boundaries

- One job consumes Claude quota and a Scaleway container (concurrency 1 — a new run queues behind a running one). Don't launch jobs for trivial work.
- Keep the prompt self-contained and the knowledge curated — bloat costs tokens and money. If the background is large, ship it as a `context.md` alongside the data (via `publish_dataset`) and tell the worker to read it first.
