"""Metabase cards inventory — queries PostgreSQL cache tables."""

import json
from dataclasses import dataclass
from typing import Optional

from web.db import get_db

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
    def from_row(cls, row: dict) -> "Card":
        return cls(
            id=row["id"],
            name=row["name"],
            description=row.get("description"),
            collection_id=row.get("collection_id"),
            dashboard_id=row.get("dashboard_id"),
            topic=row.get("topic"),
            sql_query=row.get("sql_query"),
            tables_referenced=json.loads(row["tables_json"]) if row.get("tables_json") else [],
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
    def from_row(cls, row: dict) -> "Dashboard":
        return cls(
            id=row["id"],
            name=row["name"],
            description=row.get("description"),
            topic=row.get("topic"),
            pilotage_url=row.get("pilotage_url"),
            collection_id=row.get("collection_id"),
        )


class CardsDB:
    def __init__(self, instance: str = "stats"):
        self.instance = instance

    def get(self, card_id: int) -> Optional[Card]:
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM metabase_cards WHERE id = %s AND instance = %s", (card_id, self.instance)
            ).fetchone()
            return Card.from_row(row) if row else None

    def all(self) -> list[Card]:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM metabase_cards WHERE instance = %s ORDER BY id", (self.instance,)
            ).fetchall()
            return [Card.from_row(r) for r in rows]

    def by_topic(self, topic: str) -> list[Card]:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM metabase_cards WHERE instance = %s AND topic = %s ORDER BY id",
                (self.instance, topic),
            ).fetchall()
            return [Card.from_row(r) for r in rows]

    def search(self, query: str, limit: int = 50) -> list[Card]:
        with get_db() as conn:
            rows = conn.execute(
                """SELECT * FROM metabase_cards
                   WHERE instance = %s
                     AND (name ILIKE %s OR description ILIKE %s OR sql_query ILIKE %s)
                   ORDER BY name LIMIT %s""",
                (self.instance, f"%{query}%", f"%{query}%", f"%{query}%", limit),
            ).fetchall()
            return [Card.from_row(r) for r in rows]

    def by_table(self, table_name: str) -> list[Card]:
        with get_db() as conn:
            rows = conn.execute(
                """SELECT * FROM metabase_cards
                   WHERE instance = %s AND tables_json ILIKE %s ORDER BY id""",
                (self.instance, f"%{table_name}%"),
            ).fetchall()
            return [Card.from_row(r) for r in rows]

    def by_dashboard(self, dashboard_id: int) -> list[Card]:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM metabase_cards WHERE instance = %s AND dashboard_id = %s ORDER BY id",
                (self.instance, dashboard_id),
            ).fetchall()
            return [Card.from_row(r) for r in rows]

    def topics_summary(self) -> dict[str, int]:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT topic, COUNT(*) as count FROM metabase_cards WHERE instance = %s GROUP BY topic ORDER BY count DESC",
                (self.instance,),
            ).fetchall()
            return {r["topic"] or "autre": r["count"] for r in rows}

    def count(self) -> int:
        with get_db() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as n FROM metabase_cards WHERE instance = %s", (self.instance,)
            ).fetchone()
            return row["n"]

    def get_dashboard(self, dashboard_id: int) -> Optional[Dashboard]:
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM metabase_dashboards WHERE id = %s AND instance = %s",
                (dashboard_id, self.instance),
            ).fetchone()
            return Dashboard.from_row(row) if row else None

    def all_dashboards(self) -> list[Dashboard]:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM metabase_dashboards WHERE instance = %s ORDER BY id", (self.instance,)
            ).fetchall()
            return [Dashboard.from_row(r) for r in rows]


def load_cards_db(instance: str = "stats") -> CardsDB:
    return CardsDB(instance)
