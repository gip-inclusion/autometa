"""Erreurs partagées par les modules des tableaux de bord — un module feuille, sans import applicatif."""


class DashboardNotFound(Exception):
    """Raised when a slug doesn't resolve to an existing dashboard row."""
