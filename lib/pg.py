"""Shared PostgreSQL query result type."""

from dataclasses import dataclass


@dataclass
class QueryResult:
    columns: list[str]
    rows: list[list]
    row_count: int

    def to_markdown(self, max_rows: int = 50) -> str:
        if not self.columns:
            return "(no results)"
        header = "| " + " | ".join(self.columns) + " |"
        sep = "| " + " | ".join("---" for _ in self.columns) + " |"
        lines = [header, sep]
        for row in self.rows[:max_rows]:
            lines.append("| " + " | ".join(str(v) if v is not None else "" for v in row) + " |")
        if self.row_count > max_rows:
            lines.append(f"_({self.row_count - max_rows} lignes supplémentaires)_")
        return "\n".join(lines)
