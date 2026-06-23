"""Deployment environment and the capabilities each value grants."""

from enum import StrEnum


class Environment(StrEnum):
    DEV = "dev"
    REVIEW = "review"
    STAGING = "staging"
    PROD = "prod"

    @classmethod
    def current(cls, raw: str | None) -> "Environment":
        """Resolve the configured value; unset/empty is local dev, anything unknown fails loud."""
        if not raw:
            return cls.DEV
        return cls(raw)

    @property
    def is_server(self) -> bool:
        """True on any deployed instance: write-guard active, agents run unsandboxed."""
        return self is not Environment.DEV

    @property
    def owns_shared_db(self) -> bool:
        """True only for prod, the single instance that maintains the shared autometa_tables_db."""
        return self is Environment.PROD
