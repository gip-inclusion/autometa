"""Metabase cards inventory — queries PostgreSQL cache tables."""

import json
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import func, or_, select

from web.db import get_db
from web.models import MetabaseCard, MetabaseDashboard

TOPICS = {
    "file-active": "Candidats dans la file active (30+ days waiting)",
    "postes-tension": "Postes en tension (difficult to recruit)",
    "demographie": "Age, gender, geographic breakdowns",
    "candidatures": "Candidature metrics, states, flows",
    "employeurs": "SIAE and employer information",
    "prescripteurs": "Prescripteur and orientation data",
    "auto-prescription": "Auto-prescription metrics",
    "controles": "Control and compliance",
    "prolongations": "PASS extensions",
    "etp-effectifs": "ETP and workforce metrics",
    "esat": "ESAT-specific data",
    "pass-iae": "PASS IAE delivery and tracking",
}

TABLE_TO_TOPIC = {
    "esat": "esat",
    "questionnaire": "esat",
    "candidat": "candidatures",
    "candidature": "candidatures",
    "prolongation": "prolongations",
    "pass_iae": "pass-iae",
    "pass-iae": "pass-iae",
    "suivi_pass": "pass-iae",
    "prescripteur": "prescripteurs",
    "orientation": "prescripteurs",
    "auto_prescription": "auto-prescription",
    "controle": "controles",
    "structure": "employeurs",
    "organisation": "employeurs",
    "siae": "employeurs",
    "convention": "employeurs",
    "poste": "postes-tension",
    "tension": "postes-tension",
    "file_active": "file-active",
    "recherche_active": "file-active",
    "age": "demographie",
    "genre": "demographie",
    "sexe": "demographie",
    "departement": "demographie",
    "region": "demographie",
    "etp": "etp-effectifs",
    "effectif": "etp-effectifs",
}


@dataclass
class Card:
    id: int
    name: str
    description: Optional[str]
    collection_id: Optional[int]
    dashboard_id: Optional[int]
    topic: Optional[str]
    sql_query: Optional[str]
    tables_referenced: list[str]

    @classmethod
    def from_model(cls, m: "MetabaseCard") -> "Card":
        return cls(
            id=m.id,
            name=m.name,
            description=m.description,
            collection_id=m.collection_id,
            dashboard_id=m.dashboard_id,
            topic=m.topic,
            sql_query=m.sql_query,
            tables_referenced=json.loads(m.tables_json) if m.tables_json else [],
        )


@dataclass
class Dashboard:
    id: int
    name: str
    description: Optional[str]
    topic: Optional[str]
    pilotage_url: Optional[str]
    collection_id: Optional[int]

    @classmethod
    def from_model(cls, m: "MetabaseDashboard") -> "Dashboard":
        return cls(
            id=m.id,
            name=m.name,
            description=m.description,
            topic=m.topic,
            pilotage_url=m.pilotage_url,
            collection_id=m.collection_id,
        )


class CardsDB:
    def __init__(self, instance: str = "stats"):
        self.instance = instance

    def get(self, card_id: int) -> Optional[Card]:
        with get_db() as session:
            m = session.execute(
                select(MetabaseCard).where(MetabaseCard.id == card_id, MetabaseCard.instance == self.instance)
            ).scalar_one_or_none()
            return Card.from_model(m) if m else None

    def all(self) -> list[Card]:
        with get_db() as session:
            rows = session.scalars(
                select(MetabaseCard).where(MetabaseCard.instance == self.instance).order_by(MetabaseCard.id)
            ).all()
            return [Card.from_model(m) for m in rows]

    def by_topic(self, topic: str) -> list[Card]:
        with get_db() as session:
            rows = session.scalars(
                select(MetabaseCard)
                .where(MetabaseCard.instance == self.instance, MetabaseCard.topic == topic)
                .order_by(MetabaseCard.id)
            ).all()
            return [Card.from_model(m) for m in rows]

    def search(self, query: str, limit: int = 50) -> list[Card]:
        pattern = f"%{query}%"
        with get_db() as session:
            rows = session.scalars(
                select(MetabaseCard)
                .where(
                    MetabaseCard.instance == self.instance,
                    or_(
                        MetabaseCard.name.ilike(pattern),
                        MetabaseCard.description.ilike(pattern),
                        MetabaseCard.sql_query.ilike(pattern),
                    ),
                )
                .order_by(MetabaseCard.name)
                .limit(limit)
            ).all()
            return [Card.from_model(m) for m in rows]

    def by_table(self, table_name: str) -> list[Card]:
        with get_db() as session:
            rows = session.scalars(
                select(MetabaseCard)
                .where(MetabaseCard.instance == self.instance, MetabaseCard.tables_json.ilike(f"%{table_name}%"))
                .order_by(MetabaseCard.id)
            ).all()
            return [Card.from_model(m) for m in rows]

    def by_dashboard(self, dashboard_id: int) -> list[Card]:
        with get_db() as session:
            rows = session.scalars(
                select(MetabaseCard)
                .where(MetabaseCard.instance == self.instance, MetabaseCard.dashboard_id == dashboard_id)
                .order_by(MetabaseCard.id)
            ).all()
            return [Card.from_model(m) for m in rows]

    def topics_summary(self) -> dict[str, int]:
        with get_db() as session:
            rows = session.execute(
                select(MetabaseCard.topic, func.count())
                .where(MetabaseCard.instance == self.instance)
                .group_by(MetabaseCard.topic)
                .order_by(func.count().desc())
            ).all()
            return {(topic or "autre"): count for topic, count in rows}

    def count(self) -> int:
        with get_db() as session:
            return session.scalar(
                select(func.count()).select_from(MetabaseCard).where(MetabaseCard.instance == self.instance)
            )

    def get_dashboard(self, dashboard_id: int) -> Optional[Dashboard]:
        with get_db() as session:
            m = session.execute(
                select(MetabaseDashboard).where(
                    MetabaseDashboard.id == dashboard_id, MetabaseDashboard.instance == self.instance
                )
            ).scalar_one_or_none()
            return Dashboard.from_model(m) if m else None

    def all_dashboards(self) -> list[Dashboard]:
        with get_db() as session:
            rows = session.scalars(
                select(MetabaseDashboard).where(MetabaseDashboard.instance == self.instance).order_by(MetabaseDashboard.id)
            ).all()
            return [Dashboard.from_model(m) for m in rows]


def load_cards_db(instance: str = "stats") -> CardsDB:
    return CardsDB(instance)
