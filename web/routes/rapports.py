"""Rapports HTML routes."""

from flask import Blueprint, render_template, request

from ..storage import store
from .html import get_sidebar_data

bp = Blueprint("rapports", __name__)


@bp.route("/rapports")
def rapports():
    """Rapports section - saved reports browser."""
    data = get_sidebar_data()
    report_id = request.args.get("id", type=int)

    current_report = None
    if report_id:
        current_report = store.get_report(report_id)

    reports = store.list_reports(limit=50) if not current_report else []

    return render_template(
        "rapports.html",
        section="rapports",
        current_report=current_report,
        reports=reports,
        **data
    )
