# speckit_plan — Create technical plan

## When to use

Use this skill after the spec is finalized. The plan turns requirements into
a technical architecture — HOW to build what the spec describes.

## Usage

```bash
python -m skills.speckit_plan.scripts.save_plan \
    --workdir <project-workdir> \
    --file /tmp/plan.md \
    [--version v1]
```

## Plan Template

```markdown
# Technical Plan

## Architecture
- Backend: [framework, language]
- Frontend: [approach]
- Database: [type, schema overview]

## Data Model
- [Table/collection descriptions]

## API / Pages
- [Endpoint or page list with methods]

## Dependencies
- [Python packages, JS libraries, external services]

## LLM Integration (if applicable)
- API: Synthetic (OpenAI-compatible, env vars injected at deploy)
- Model: [model name, e.g. llama3.2]
- Usage: [what LLM is used for — chat, summarization, etc.]
- Helper: llm.py scaffolded via expert_llm skill

## Deployment
- Docker setup
- Environment variables needed
- Port mappings
```

## Guidelines

- Reference the spec: every architectural choice should trace back to a requirement
- Be concrete: name specific libraries, frameworks, file paths
- Include the Dockerfile and docker-compose.yml approach (use `${HOST_PORT}` for port mapping)
- Keep it actionable — someone should be able to start coding from this
