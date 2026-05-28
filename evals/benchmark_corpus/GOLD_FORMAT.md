# Gold annotation format

Each gold annotation is a JSON file at `s3://<bucket>/<prefix>gold/<short-id>.json` annotating one session at `sessions/<short-id>*.jsonl`.

## Schema

```json
{
  "session_id": "<uuid>",
  "version": 1,
  "annotator": "<name>",
  "annotated_at": "<iso8601>",
  "conversation_level": {
    "overall_quality": 1-5,
    "correctness": 1-5,
    "completeness": 1-5,
    "helpfulness": 1-5,
    "style": 1-5,
    "tags": ["sql", "matomo", ...],
    "difficulty": "trivial|easy|medium|hard|expert",
    "expected_skills": ["metabase_query", ...]
  },
  "turns": [
    {
      "turn_index": 0,
      "user_message_uuid": "<uuid>",
      "is_correction": false,
      "gold_sql": "SELECT ...",
      "gold_sql_alternatives": [...],
      "gold_answer": "<text>",
      "acceptable_alternatives": [...],
      "gold_action_trace": [{"tool": "Read", "target": "..."}, ...],
      "expected_knowledge_reads": ["knowledge/..."],
      "expected_source": "metabase|matomo|autometa_tables_db",
      "expected_instance": "stats|rdvi|..."
    }
  ]
}
```

## Conventions

- **Versioning**: increment `version` on each substantive edit; corpus JSONLs are immutable.
- **Multi-reference**: any field with `_alternatives` accepts a list of acceptable values; metrics take `max` across alternatives.
- **Naming**: gold files use the first 8 chars of the session UUID (`<short-id>.json`).
- **PII**: emails/phones/IDs must be pseudonymized before pushing to S3.

## Loading

`lib.harness_eval.parse_gold_json(text)` → `Gold` dataclass. `lib.eval_corpus.load_gold(short_id)` for S3.
