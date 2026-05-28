"""Admin route: harness evaluation runs viewer."""

from fastapi import APIRouter, Depends, HTTPException, Request

from lib import eval_corpus
from lib.harness_eval import diff_runs

from . import config
from .deps import get_current_user, templates

router = APIRouter()


METRIC_LABELS_FR: dict[str, tuple[str, str]] = {
    "sql_syntactic_validity": (
        "Validité syntaxique du SQL",
        "Part des requêtes SQL générées par l'agent qui parsent sans erreur (sqlglot, fallback en cas d'absence).",
    ),
    "correction_rate": (
        "Absence de correction utilisateur",
        "1 moins la fraction de tours utilisateur contenant des mots-clés de correction (« non », « pas ça », « plutôt »…).",
    ),
    "tool_chain_length": (
        "Concision des chaînes d'outils",
        "1 / (1 + max_chain / 10) où max_chain est le plus long enchaînement d'appels d'outils par tour. Pénalise les sessions verbeuses.",
    ),
    "knowledge_utilization": (
        "Lecture de la base de connaissance",
        "Vrai si l'agent lit au moins un fichier knowledge/ avant son premier appel d'API (Bash, Skill, Task).",
    ),
    "hallucination_signals": (
        "Absence d'hallucination",
        "Pénalise les références à des identifiants Matomo (idSite=) inconnus dans le texte, la pensée ou le SQL.",
    ),
    "token_efficiency": (
        "Efficience des tokens",
        "Composite du ratio output/total et du taux de cache hit. Mesure si l'agent dépense ses tokens pour produire ou pour reconsommer.",
    ),
    "sql_presence": (
        "Présence de SQL attendue",
        "Vrai si une session qui pose une question data (« combien », « statistiques »…) produit au moins une requête SQL.",
    ),
    "expected_skills_used": (
        "Skills attendus invoqués",
        "Fraction des skills déclarés expected_skills dans le gold qui ont effectivement été appelés via tool_use Skill.",
    ),
    "overall_quality": (
        "Qualité globale (gold)",
        "Score humain overall_quality de 1 à 5 (annotation gold), normalisé en 0–1.",
    ),
}


def _label(metric_name: str) -> str:
    return METRIC_LABELS_FR.get(metric_name, (metric_name, ""))[0]


def _desc(metric_name: str) -> str:
    return METRIC_LABELS_FR.get(metric_name, ("", ""))[1]


def _require_admin(user_email: str) -> None:
    if user_email not in config.ADMIN_USERS:
        raise HTTPException(status_code=403, detail="Admin only")


@router.get("/harness-eval")
def list_runs_page(request: Request, user_email: str = Depends(get_current_user)):
    """List all benchmark runs persisted in S3."""
    _require_admin(user_email)
    runs = eval_corpus.list_runs()
    return templates.TemplateResponse(
        request,
        "harness_eval/list.html",
        {
            "section": "harness_eval",
            "runs": runs,
            "n_sessions": len(eval_corpus.list_sessions()),
            "metric_label": _label,
            "metric_desc": _desc,
        },
    )


@router.get("/harness-eval/runs/{run_id}")
def view_run_page(run_id: str, request: Request, user_email: str = Depends(get_current_user)):
    """View a single run's aggregate scores and per-session breakdown."""
    _require_admin(user_email)
    result = eval_corpus.load_run(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    runs = eval_corpus.list_runs()
    return templates.TemplateResponse(
        request,
        "harness_eval/run.html",
        {
            "section": "harness_eval",
            "result": result,
            "other_runs": [r for r in runs if r["run_id"] != run_id],
            "metric_label": _label,
            "metric_desc": _desc,
        },
    )


@router.get("/harness-eval/diff")
def diff_runs_page(
    request: Request,
    baseline: str,
    variant: str,
    user_email: str = Depends(get_current_user),
):
    """Diff two runs side by side."""
    _require_admin(user_email)
    b = eval_corpus.load_run(baseline)
    v = eval_corpus.load_run(variant)
    if b is None or v is None:
        raise HTTPException(status_code=404, detail="One or both runs not found")
    diff = diff_runs(b, v)
    return templates.TemplateResponse(
        request,
        "harness_eval/diff.html",
        {
            "section": "harness_eval",
            "diff": diff,
            "baseline": b,
            "variant": v,
            "metric_label": _label,
            "metric_desc": _desc,
        },
    )
