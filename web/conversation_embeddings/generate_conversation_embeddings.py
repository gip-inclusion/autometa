import argparse
import hashlib
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sentence_transformers import SentenceTransformer
from sqlalchemy import text

from web import config
from web.db import get_engine

logger = logging.getLogger(__name__)


def content_hash(content):
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def content_preview(content):
    return content[: config.EMBEDDING_CONTENT_PREVIEW_LENGTH]


def to_pgvector(values):
    return "[" + ",".join(str(float(value)) for value in values) + "]"


def resolve_time_window(days_ago):
    if days_ago is None:
        return None, None

    timezone = ZoneInfo(config.DISPLAY_TIMEZONE)
    target_date = datetime.now(timezone).date() - timedelta(days=days_ago)

    start_at = datetime.combine(target_date, datetime.min.time(), tzinfo=timezone)
    end_at = start_at + timedelta(days=1)

    return start_at, end_at


def load_candidate_messages(connection, limit, start_at=None, end_at=None):
    limit_clause = "limit :limit" if limit else ""
    time_filter = "and m.timestamp >= :start_at and m.timestamp < :end_at" if start_at else ""

    query = text(f"""
    select
        m.id as message_id,
        m.conversation_id,
        c.user_id,
        m.role,
        m.content,
        m.timestamp::timestamptz as message_timestamp,
        e.content_hash as existing_content_hash
    from messages m
    join conversations c
        on c.id = m.conversation_id
    left join conversation_message_embeddings e
        on e.message_id = m.id
        and e.embedding_model = :embedding_model
    where m.role in ('user', 'assistant', 'report')
      and nullif(trim(m.content), '') is not null
      and (m.role <> 'assistant' or c.needs_response = 0)
      {time_filter}
    order by m.id
    {limit_clause}
    """)

    params = {"embedding_model": config.EMBEDDING_MODEL}

    if limit:
        params["limit"] = limit

    if start_at:
        params["start_at"] = start_at
        params["end_at"] = end_at

    return connection.execute(query, params).mappings().all()


def prepare_messages(rows):
    messages = []

    for row in rows:
        current_hash = content_hash(row["content"])

        if row["existing_content_hash"] == current_hash:
            continue

        messages.append({
            "message_id": row["message_id"],
            "conversation_id": row["conversation_id"],
            "user_id": row["user_id"],
            "role": row["role"],
            "content": row["content"],
            "content_hash": current_hash,
            "content_length": len(row["content"]),
            "content_preview": content_preview(row["content"]),
            "message_timestamp": row["message_timestamp"],
        })

    return messages


def insert_embeddings(connection, messages, embeddings):
    params = []

    for message, embedding in zip(messages, embeddings, strict=True):
        params.append({
            "message_id": message["message_id"],
            "conversation_id": message["conversation_id"],
            "user_id": message["user_id"],
            "role": message["role"],
            "content_hash": message["content_hash"],
            "content_length": message["content_length"],
            "content_preview": message["content_preview"],
            "message_timestamp": message["message_timestamp"],
            "embedding_model": config.EMBEDDING_MODEL,
            "embedding": to_pgvector(embedding),
        })

    if not params:
        return 0

    query = text("""
        insert into conversation_message_embeddings (
            message_id,
            conversation_id,
            user_id,
            role,
            content_hash,
            content_length,
            content_preview,
            message_timestamp,
            embedding_model,
            embedding
        )
        values (
            :message_id,
            :conversation_id,
            :user_id,
            :role,
            :content_hash,
            :content_length,
            :content_preview,
            :message_timestamp,
            :embedding_model,
            cast(:embedding as vector)
        )
        on conflict (message_id, embedding_model)
        do update set
            conversation_id = excluded.conversation_id,
            user_id = excluded.user_id,
            role = excluded.role,
            content_hash = excluded.content_hash,
            content_length = excluded.content_length,
            content_preview = excluded.content_preview,
            message_timestamp = excluded.message_timestamp,
            embedding = excluded.embedding,
            updated_at = now()
        where conversation_message_embeddings.content_hash is distinct from excluded.content_hash
        """)

    connection.execute(query, params)

    return len(params)


def generate_embeddings(limit, batch_size, days_ago):
    engine = get_engine()
    start_at, end_at = resolve_time_window(days_ago)

    logger.info("Loading embedding model: %s", config.EMBEDDING_MODEL)
    model = SentenceTransformer(config.EMBEDDING_MODEL, device="cpu")

    if start_at and end_at:
        logger.info("Embedding messages from %s to %s", start_at, end_at)

    with engine.begin() as connection:
        rows = load_candidate_messages(
            connection,
            limit=limit,
            start_at=start_at,
            end_at=end_at,
        )

    logger.info("Loaded %s candidate messages", len(rows))

    messages = prepare_messages(rows)

    if not messages:
        logger.info("No messages to embed")
        return

    logger.info("Generating embeddings for %s messages", len(messages))

    total_inserted = 0

    for start in range(0, len(messages), batch_size):
        batch = messages[start : start + batch_size]
        texts = [f"passage: {message['content']}" for message in batch]

        embeddings = model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
        )

        with engine.begin() as connection:
            inserted = insert_embeddings(connection, batch, embeddings)

        total_inserted += inserted

        logger.info(
            "Processed %s/%s messages",
            min(start + batch_size, len(messages)),
            len(messages),
        )

    logger.info(
        "Embedding generation finished. Inserted or updated %s embeddings",
        total_inserted,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=config.EMBEDDING_BATCH_SIZE)
    parser.add_argument("--days-ago", type=int, default=None)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    generate_embeddings(
        limit=args.limit,
        batch_size=args.batch_size,
        days_ago=args.days_ago,
    )


if __name__ == "__main__":
    main()
