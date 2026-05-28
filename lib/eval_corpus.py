"""S3-backed eval corpus and results storage."""

import logging
from pathlib import Path

from lib.harness_eval import (
    Gold,
    RunResult,
    Session,
    parse_gold_json,
    parse_session_jsonl,
    run_result_from_json,
    run_result_to_json,
)
from web import s3

logger = logging.getLogger(__name__)


def list_sessions() -> list[str]:
    """Return session IDs available in S3 (strips .jsonl suffix)."""
    files = s3.eval_corpus.list_files("sessions/")
    return sorted(
        f["path"].removeprefix("sessions/").removesuffix(".jsonl") for f in files if f["path"].endswith(".jsonl")
    )


def load_session(session_id: str) -> Session | None:
    """Load and parse a session from S3."""
    blob = s3.eval_corpus.download(f"sessions/{session_id}.jsonl")
    if blob is None:
        return None
    return parse_session_jsonl(blob.decode("utf-8"), session_id=session_id)


def load_all_sessions() -> list[Session]:
    """Load and parse all sessions from S3."""
    sessions = []
    for sid in list_sessions():
        s = load_session(sid)
        if s is not None:
            sessions.append(s)
    return sessions


def list_golds() -> list[str]:
    """Return gold annotation IDs available in S3."""
    files = s3.eval_corpus.list_files("gold/")
    return sorted(f["path"].removeprefix("gold/").removesuffix(".json") for f in files if f["path"].endswith(".json"))


def load_gold(gold_id: str) -> Gold | None:
    """Load and parse a gold annotation from S3."""
    blob = s3.eval_corpus.download(f"gold/{gold_id}.json")
    if blob is None:
        return None
    return parse_gold_json(blob.decode("utf-8"))


def list_runs() -> list[dict]:
    """Return run metadata sorted by recency (most recent first)."""
    files = s3.eval_corpus.list_files("results/")
    runs = []
    for f in files:
        if not f["path"].endswith(".json"):
            continue
        runs.append({
            "run_id": f["path"].removeprefix("results/").removesuffix(".json"),
            "size": f["size"],
            "last_modified": f["last_modified"],
        })
    return sorted(runs, key=lambda r: r["last_modified"], reverse=True)


def load_run(run_id: str) -> RunResult | None:
    """Load a previously persisted RunResult from S3."""
    blob = s3.eval_corpus.download(f"results/{run_id}.json")
    if blob is None:
        return None
    return run_result_from_json(blob.decode("utf-8"))


def persist_run(result: RunResult) -> bool:
    """Upload a RunResult JSON to S3."""
    body = run_result_to_json(result).encode("utf-8")
    return s3.eval_corpus.upload(f"results/{result.run_id}.json", body, content_type="application/json")


def push_local_corpus(local_dir: Path, *, subpath: str = "") -> int:
    """Upload a local directory tree to s3://eval_corpus/<subpath>. Returns file count."""
    count = 0
    for path in sorted(local_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(local_dir).as_posix()
        key = f"{subpath}{rel}" if subpath else rel
        if s3.eval_corpus.upload(key, path.read_bytes()):
            count += 1
        else:
            logger.error("Failed to upload %s", key)
    return count


def pull_corpus_to_dir(local_dir: Path, *, subpath: str = "") -> int:
    """Download s3://eval_corpus/<subpath> into a local directory tree. Returns file count."""
    local_dir.mkdir(parents=True, exist_ok=True)
    files = s3.eval_corpus.list_files(subpath)
    count = 0
    for f in files:
        rel = f["path"].removeprefix(subpath) if subpath else f["path"]
        dest = local_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        blob = s3.eval_corpus.download(f["path"])
        if blob is None:
            logger.warning("Failed to download %s", f["path"])
            continue
        dest.write_bytes(blob)
        count += 1
    return count
