"""Generate data.json for the actes-metier interactive dashboard (v5)."""

import json
from collections import defaultdict
from datetime import datetime, timezone

from lib.query import CallerType, execute_matomo_query, execute_metabase_query

OUTPUT = "/app/data/interactive/actes-metier/data.json"
MONTHS = [
    "2025-04", "2025-05", "2025-06", "2025-07", "2025-08", "2025-09", "2025-10",
    "2025-11", "2025-12", "2026-01", "2026-02", "2026-03", "2026-04",
]
START_DATE = "2025-04-01"
CALLER = CallerType.AGENT

STRUCT_MAP = {
    # France Travail
    "FT": "FRANCE_TRAVAIL", "PE": "FRANCE_TRAVAIL", "france_travail": "FRANCE_TRAVAIL",
    # Mission locale
    "ML": "MISSION_LOCALE", "mission_locale": "MISSION_LOCALE",
    # Cap emploi
    "CAP_EMPLOI": "CAP_EMPLOI", "cap_emploi": "CAP_EMPLOI",
    # Conseil départemental
    "DEPT": "CONSEIL_DEPARTEMENTAL", "CD": "CONSEIL_DEPARTEMENTAL",
    "conseil_departemental": "CONSEIL_DEPARTEMENTAL",
    # Délégataire RSA
    "ODC": "DELEGATAIRE_RSA", "delegataire_rsa": "DELEGATAIRE_RSA",
    "DELEGATAIRE_RSA": "DELEGATAIRE_RSA",
    # CCAS/CIAS
    "CCAS": "CCAS_CIAS", "CIAS": "CCAS_CIAS", "ASE": "CCAS_CIAS",
    # Justice/Probation
    "SPIP": "JUSTICE_PROBATION", "PJJ": "JUSTICE_PROBATION", "JUSTICE": "JUSTICE_PROBATION",
    # Hébergement
    "CHU": "TS_HEBERGEMENT", "CHRS": "TS_HEBERGEMENT", "CPH": "TS_HEBERGEMENT",
    "CADA": "TS_HEBERGEMENT", "HUDA": "TS_HEBERGEMENT", "RS_FJT": "TS_HEBERGEMENT",
    "OIL": "TS_HEBERGEMENT", "PENSION": "TS_HEBERGEMENT", "ACT": "TS_HEBERGEMENT",
    "LHSS": "TS_HEBERGEMENT",
    "CHRS/Accueil de jour": "TS_HEBERGEMENT", "Accueil de jour": "TS_HEBERGEMENT",
    # SIAE
    "EI": "SIAE", "AI": "SIAE", "ACI": "SIAE", "ETTI": "SIAE", "EITI": "SIAE",
    "GEIQ": "SIAE", "EA": "SIAE", "EATT": "SIAE", "OPCS": "SIAE",
    "siae": "SIAE", "employer": "SIAE",
    "Groupements d\u2019employeurs pour l\u2019insertion et la qualification": "SIAE",
    # PLIE
    "PLIE": "PLIE",
    # E2C/Épide/AFPA
    "E2C": "E2C_EPIDE_AFPA", "EPIDE": "E2C_EPIDE_AFPA",
    "AFPA": "E2C_EPIDE_AFPA", "OF": "E2C_EPIDE_AFPA",
    "Organisme de formation": "E2C_EPIDE_AFPA",
    # TS spécialisés
    "CIDFF": "TS_SPECIALISES", "CSAPA": "TS_SPECIALISES", "CAARUD": "TS_SPECIALISES",
    "PREVENTION": "TS_SPECIALISES", "OHPD": "TS_SPECIALISES", "OCASF": "TS_SPECIALISES",
    # CAF/MSA
    "CAF": "CAF_MSA", "MSA": "CAF_MSA",
    # Autres insertion
    "PIJ_BIJ": "AUTRES_INSERTION", "OACAS": "AUTRES_INSERTION", "CAVA": "AUTRES_INSERTION",
    # Monrecap labels that map directly
    "SIAE": "SIAE",
    # Marché user kinds
    "BUYER": "Autre", "PARTNER": "Autre", "INDIVIDUAL": "Autre", "ADMIN": "Autre",
}


def map_struct(raw):
    if not raw:
        return "Autre"
    return STRUCT_MAP.get(str(raw).strip(), "Autre")


def map_struct_diag(raw):
    """Extract type code from 'Prescripteur FT' or 'Employeur AI' format."""
    if not raw:
        return "Autre"
    parts = str(raw).strip().split(" ", 1)
    return STRUCT_MAP.get(parts[1].strip(), "Autre") if len(parts) == 2 else "Autre"


def to_rows(result):
    """Convert Metabase result (columns + rows) to a list of dicts."""
    cols = result.data["columns"]
    return [dict(zip(cols, row)) for row in result.data["rows"]]


def parse_dept(val):
    """Normalize a raw department value to a 2-3 char INSEE code, or 'Inconnu'."""
    if not val:
        return "Inconnu"
    s = str(val).strip()
    if " - " in s:
        s = s.split(" - ")[0].strip()
    if not s:
        return "Inconnu"
    if s.upper() in ("2A", "2B"):
        return s.upper()
    if s.isdigit():
        n = int(s)
        if 1 <= n <= 95:
            return f"{n:02d}"
        if 971 <= n <= 976:
            return str(n)
    return "Inconnu"


def rec(mois, source, type_acte, categorie, north_star, type_structure, n, traite=None, departement="Inconnu"):
    return {
        "mois": mois,
        "source": source,
        "type_acte": type_acte,
        "categorie_acte": categorie,
        "north_star": north_star,
        "traite": north_star if traite is None else traite,
        "type_structure": type_structure,
        "departement": departement,
        "nombre_actes": n,
    }


_RDVI_TYPE_MAP = {
    "rsa_orientation":    "Invitation à un RDV d\u2019orientation",
    "rsa_accompagnement": "Invitation à un RDV d\u2019accompagnement",
    "siae":               "Invitation à un Entretien SIAE",
    "autre":              "Invitation à un Autre RDV",
}


def fetch_rdvi():
    """RDV-i invitations — acte = invitation, NS = invitation avec RDV réservé."""
    sql = f"""
    WITH inv_org AS (
        SELECT DISTINCT ON (io.invitation_id)
            io.invitation_id,
            o.organisation_type
        FROM rdvi.invitations_organisations io
        JOIN rdvi.organisations o ON o.id = io.organisation_id
        ORDER BY io.invitation_id, o.organisation_type NULLS LAST
    )
    SELECT
        TO_CHAR(DATE_TRUNC('month', i.created_at), 'YYYY-MM') AS mois,
        mc.motif_category_type,
        COALESCE(io.organisation_type, 'autre') AS organisation_type,
        COALESCE(d.number, 'Inconnu') AS departement,
        COUNT(DISTINCT i.id) AS nb_invitations,
        COUNT(DISTINCT CASE WHEN r.uuid IS NOT NULL THEN i.id END) AS nb_with_rdv
    FROM rdvi.invitations i
    LEFT JOIN rdvi.follow_ups fu ON i.follow_up_id = fu.id
    LEFT JOIN rdvi.participations p ON i.follow_up_id = p.follow_up_id
    LEFT JOIN rdvi.rdvs r ON p.rdv_id = r.id
    LEFT JOIN rdvi.motif_categories mc ON fu.motif_category_id = mc.id
    LEFT JOIN inv_org io ON io.invitation_id = i.id
    LEFT JOIN rdvi.departments d ON d.id = i.department_id
    WHERE i.created_at >= '{START_DATE}'
      AND i.created_at < DATE_TRUNC('month', NOW())
    GROUP BY 1, 2, 3, 4
    ORDER BY 1, 2, 3, 4
    """
    result = execute_metabase_query(instance="rdvi", caller=CALLER, sql=sql, database_id=2)
    if not result.success:
        raise RuntimeError(f"rdvi: {result.error}")
    rows = []
    for row in to_rows(result):
        label = _RDVI_TYPE_MAP.get(row["motif_category_type"], row["motif_category_type"])
        ts = map_struct(row["organisation_type"])
        dept = parse_dept(row["departement"])
        nb_with = int(row["nb_with_rdv"])
        nb_sans = int(row["nb_invitations"]) - nb_with
        if nb_with > 0:
            rows.append(rec(row["mois"], "rdvi", label, "Accompagnement", True, ts, nb_with, departement=dept))
        if nb_sans > 0:
            rows.append(rec(row["mois"], "rdvi", label, "Accompagnement", False, ts, nb_sans, departement=dept))
    return rows


def fetch_emplois_candidatures():
    """Candidatures emplois (hors injection IA) par état et type de prescripteur."""
    sql = f"""
    SELECT
        TO_CHAR(DATE_TRUNC('month', date_candidature), 'YYYY-MM') AS mois,
        état NOT IN ('Nouvelle candidature', 'Candidature en attente',
                     'Candidature à l''étude')
        AND date_traitement IS NOT NULL
        AND CAST(date_traitement AS DATE) - CAST(date_candidature AS DATE) BETWEEN 0 AND 30
            AS north_star,
        état NOT IN ('Nouvelle candidature', 'Candidature en attente',
                     'Candidature à l''étude')
            AS traite,
        type_org_prescripteur,
        COALESCE(dept_org, 'Inconnu') AS departement,
        COUNT(*) AS nombre_actes
    FROM candidatures_echelle_locale
    WHERE date_candidature >= '{START_DATE}'
      AND date_candidature < DATE_TRUNC('month', NOW())
      AND injection_ai = 0
    GROUP BY 1, 2, 3, 4, 5
    ORDER BY 1, 2, 3, 4, 5
    """
    result = execute_metabase_query(instance="stats", caller=CALLER, sql=sql, database_id=2)
    if not result.success:
        raise RuntimeError(f"emplois candidatures: {result.error}")
    return [
        rec(row["mois"], "emplois",
            "Candidature auprès d\u2019un employeur solidaire",
            "Accompagnement", bool(row["north_star"]),
            map_struct(row["type_org_prescripteur"]), int(row["nombre_actes"]),
            traite=bool(row["traite"]),
            departement=parse_dept(row["departement"]))
        for row in to_rows(result)
    ]


def fetch_emplois_fiches():
    """Créations et mises à jour de fiches de poste (offres d'emploi)."""
    sql = f"""
    SELECT
        TO_CHAR(DATE_TRUNC('month', "date_création"), 'YYYY-MM') AS mois,
        'Création offre d\u2019emploi' AS type_acte,
        type_employeur,
        COALESCE("département_employeur", 'Inconnu') AS departement,
        COUNT(*) AS nombre_actes
    FROM fiches_de_poste
    WHERE "date_création" >= '{START_DATE}'
      AND "date_création" < DATE_TRUNC('month', NOW())
    GROUP BY 1, 2, 3, 4
    UNION ALL
    SELECT
        TO_CHAR(DATE_TRUNC('month', "date_dernière_modification"), 'YYYY-MM') AS mois,
        'Mise à jour offre d\u2019emploi' AS type_acte,
        type_employeur,
        COALESCE("département_employeur", 'Inconnu') AS departement,
        COUNT(*) AS nombre_actes
    FROM fiches_de_poste
    WHERE "date_dernière_modification" >= '{START_DATE}'
      AND "date_dernière_modification" < DATE_TRUNC('month', NOW())
      AND "date_dernière_modification" > "date_création"
    GROUP BY 1, 2, 3, 4
    ORDER BY 1, 2, 3, 4
    """
    result = execute_metabase_query(instance="stats", caller=CALLER, sql=sql, database_id=2)
    if not result.success:
        raise RuntimeError(f"emplois fiches: {result.error}")
    return [
        rec(row["mois"], "emplois", row["type_acte"],
            "Support", True,
            map_struct(row["type_employeur"]), int(row["nombre_actes"]),
            departement=parse_dept(row["departement"]))
        for row in to_rows(result)
    ]


def fetch_emplois_structures():
    """Créations d'employeurs solidaires (structures IAE)."""
    sql = f"""
    SELECT
        TO_CHAR(DATE_TRUNC('month', date_inscription), 'YYYY-MM') AS mois,
        type,
        COALESCE("département", 'Inconnu') AS departement,
        COUNT(*) AS nombre_actes
    FROM structures
    WHERE date_inscription >= '{START_DATE}'
      AND date_inscription < DATE_TRUNC('month', NOW())
    GROUP BY 1, 2, 3
    ORDER BY 1, 2, 3
    """
    result = execute_metabase_query(instance="stats", caller=CALLER, sql=sql, database_id=2)
    if not result.success:
        raise RuntimeError(f"emplois structures: {result.error}")
    return [
        rec(row["mois"], "emplois", "Création employeur solidaire",
            "Support", False,
            "SIAE", int(row["nombre_actes"]),
            departement=parse_dept(row["departement"]))
        for row in to_rows(result)
    ]


def fetch_emplois_diagnostics():
    """Diagnostics IAE réalisés (par type d'auteur)."""
    sql = f"""
    SELECT
        TO_CHAR(DATE_TRUNC('month', date_diagnostic), 'YYYY-MM') AS mois,
        sous_type_auteur_diagnostic,
        COALESCE(département_diag, 'Inconnu') AS departement,
        COUNT(DISTINCT id) AS nombre_actes
    FROM public.candidats
    WHERE date_diagnostic >= '{START_DATE}'
      AND date_diagnostic < DATE_TRUNC('month', NOW())
    GROUP BY 1, 2, 3
    ORDER BY 1, 2, 3
    """
    result = execute_metabase_query(instance="stats", caller=CALLER, sql=sql, database_id=2)
    if not result.success:
        raise RuntimeError(f"emplois diagnostics: {result.error}")
    return [
        rec(row["mois"], "emplois", "Diagnostic IAE", "Accompagnement", False,
            map_struct_diag(row["sous_type_auteur_diagnostic"]), int(row["nombre_actes"]),
            departement=parse_dept(row["departement"]))
        for row in to_rows(result)
    ]


def fetch_emplois_recherches():
    """Recherches d'offre Emplois (page views /search/employers/results, Matomo site 117)."""
    result = execute_matomo_query(
        instance="inclusion",
        caller=CALLER,
        method="VisitsSummary.get",
        params={
            "idSite": 117,
            "period": "month",
            "date": f"{START_DATE},2026-04-30",
            "segment": "pageUrl=@/search/employers/results",
        },
    )
    if not result.success:
        raise RuntimeError(f"matomo emplois recherche offre: {result.error}")
    rows = []
    for month_key, stats in result.data.items():
        mois = month_key[:7]
        if not isinstance(stats, dict):
            continue
        n = int(stats.get("nb_visits", 0))
        if n > 0:
            rows.append(rec(mois, "emplois", "Recherche d\u2019offre",
                            "Support", False, "Inconnu", n))
    return rows


def fetch_emplois_recherches_service():
    """Recherches de service depuis Emplois (page views /search/services/results, Matomo site 117)."""
    result = execute_matomo_query(
        instance="inclusion",
        caller=CALLER,
        method="VisitsSummary.get",
        params={
            "idSite": 117,
            "period": "month",
            "date": f"{START_DATE},2026-04-30",
            "segment": "pageUrl=@/search/services/results",
        },
    )
    if not result.success:
        raise RuntimeError(f"matomo emplois recherche service: {result.error}")
    rows = []
    for month_key, stats in result.data.items():
        mois = month_key[:7]
        if not isinstance(stats, dict):
            continue
        n = int(stats.get("nb_visits", 0))
        if n > 0:
            rows.append(rec(mois, "emplois", "Recherche de service",
                            "Support", False, "Inconnu", n))
    return rows


def fetch_gps():
    """Actes GPS — consultation et mise à jour de groupes de suivi."""
    sql = f"""
    SELECT
        TO_CHAR(DATE_TRUNC('month', timestamp), 'YYYY-MM') AS mois,
        CASE
            WHEN view_name IN ('gps:group_memberships', 'gps:group_beneficiary',
                               'gps:display_contact_info', 'gps:old_group_list')
                THEN 'Consultation groupe de suivi'
            ELSE 'Mise à jour groupe de suivi'
        END AS type_acte,
        type_org,
        COALESCE(dept_org, 'Inconnu') AS departement,
        COUNT(*) AS nombre_actes
    FROM gps_logs_users
    WHERE group_id IS NOT NULL
      AND view_name != 'gps:group_list'
      AND timestamp >= '{START_DATE}'
      AND timestamp < DATE_TRUNC('month', NOW())
    GROUP BY 1, 2, 3, 4
    ORDER BY 1, 2, 3, 4
    """
    result = execute_metabase_query(instance="stats", caller=CALLER, sql=sql, database_id=2)
    if not result.success:
        raise RuntimeError(f"gps: {result.error}")
    return [
        rec(row["mois"], "GPS", row["type_acte"],
            "Support", False,
            map_struct(row["type_org"]), int(row["nombre_actes"]),
            departement=parse_dept(row["departement"]))
        for row in to_rows(result)
    ]


def fetch_dora_orientations():
    """Orientations Dora — NS = orientation traitée (VALIDÉE ou REFUSÉE)."""
    sql = f"""
    SELECT
        TO_CHAR(DATE_TRUNC('month', o.creation_date), 'YYYY-MM') AS mois,
        o.status IN ('VALIDÉE', 'REFUSÉE') AS north_star,
        s.typology,
        COALESCE(s.department, 'Inconnu') AS departement,
        COUNT(*) AS nombre_actes
    FROM public.orientations_orientation o
    LEFT JOIN structures_structure s ON s.id = o.prescriber_structure_id
    WHERE o.creation_date >= '{START_DATE}'
      AND o.creation_date < DATE_TRUNC('month', NOW())
    GROUP BY 1, 2, 3, 4
    ORDER BY 1, 2, 3, 4
    """
    result = execute_metabase_query(instance="dora", caller=CALLER, sql=sql, database_id=2)
    if not result.success:
        raise RuntimeError(f"dora orientations: {result.error}")
    return [
        rec(row["mois"], "dora", "Orientation vers service", "Accompagnement",
            bool(row["north_star"]),
            map_struct(row["typology"]), int(row["nombre_actes"]),
            departement=parse_dept(row["departement"]))
        for row in to_rows(result)
    ]


def fetch_dora_imer():
    """Intentions d'orientation Dora (iMER) — acte non North Star."""
    sql = f"""
    WITH user_struct AS (
        SELECT DISTINCT ON (u.id)
            u.id AS user_id,
            s.typology
        FROM public.users_user u
        JOIN public.structures_structuremember sm ON sm.user_id = u.id
        JOIN public.structures_structure s ON s.id = sm.structure_id
        WHERE s.typology IS NOT NULL AND s.typology != ''
        ORDER BY u.id
    )
    SELECT
        TO_CHAR(DATE_TRUNC('month', im.date), 'YYYY-MM') AS mois,
        COALESCE(us.typology, '') AS typology,
        COALESCE(im.structure_department, 'Inconnu') AS departement,
        COUNT(*) AS nombre_actes
    FROM public_intermediate."int_iMER" im
    LEFT JOIN user_struct us ON us.user_id = im.user_id
    WHERE im.user_kind IN ('accompagnateur', 'accompagnateur_offreur', 'offreur')
      AND im.date >= '{START_DATE}'
      AND im.date < DATE_TRUNC('month', NOW())
    GROUP BY 1, 2, 3
    ORDER BY 1, 2, 3
    """
    result = execute_metabase_query(
        instance="dora", caller=CALLER, sql=sql, database_id=2, timeout=120,
    )
    if not result.success:
        raise RuntimeError(f"dora imer: {result.error}")
    return [
        rec(row["mois"], "dora", "Intention d\u2019orientation",
            "Support", False,
            map_struct(row["typology"]), int(row["nombre_actes"]),
            departement=parse_dept(row["departement"]))
        for row in to_rows(result)
    ]


def fetch_dora_fiches():
    """Mises à jour d'offres de service Dora."""
    sql = f"""
    SELECT
        TO_CHAR(DATE_TRUNC('month', ss.modification_date), 'YYYY-MM') AS mois,
        st.typology,
        COALESCE(st.department, 'Inconnu') AS departement,
        COUNT(*) AS nombre_actes
    FROM services_service ss
    LEFT JOIN structures_structure st ON st.id = ss.structure_id
    WHERE ss.last_editor_id IS NOT NULL
      AND ss.modification_date >= '{START_DATE}'
      AND ss.modification_date < DATE_TRUNC('month', NOW())
    GROUP BY 1, 2, 3
    ORDER BY 1, 2, 3
    """
    result = execute_metabase_query(instance="dora", caller=CALLER, sql=sql, database_id=2)
    if not result.success:
        raise RuntimeError(f"dora fiches: {result.error}")
    return [
        rec(row["mois"], "dora",
            "Mise à jour offre de service, hors emploi solidaire",
            "Support", False,
            map_struct(row["typology"]), int(row["nombre_actes"]),
            departement=parse_dept(row["departement"]))
        for row in to_rows(result)
    ]


def fetch_dora_creations_services():
    """Créations d'offres de service Dora (hors emploi solidaire)."""
    sql = f"""
    SELECT
        TO_CHAR(DATE_TRUNC('month', ss.creation_date), 'YYYY-MM') AS mois,
        st.typology,
        COALESCE(st.department, 'Inconnu') AS departement,
        COUNT(*) AS nombre_actes
    FROM services_service ss
    LEFT JOIN structures_structure st ON st.id = ss.structure_id
    WHERE ss.creation_date >= '{START_DATE}'
      AND ss.creation_date < DATE_TRUNC('month', NOW())
    GROUP BY 1, 2, 3
    ORDER BY 1, 2, 3
    """
    result = execute_metabase_query(instance="dora", caller=CALLER, sql=sql, database_id=2)
    if not result.success:
        raise RuntimeError(f"dora creations services: {result.error}")
    return [
        rec(row["mois"], "dora",
            "Création ou diffusion offre de service, hors emploi solidaire",
            "Support", False,
            map_struct(row["typology"]), int(row["nombre_actes"]),
            departement=parse_dept(row["departement"]))
        for row in to_rows(result)
    ]


def fetch_dora_creations_structures():
    """Créations de structures Dora (hors employeurs solidaires)."""
    sql = f"""
    SELECT
        TO_CHAR(DATE_TRUNC('month', creation_date), 'YYYY-MM') AS mois,
        typology,
        COALESCE(department, 'Inconnu') AS departement,
        COUNT(*) AS nombre_actes
    FROM structures_structure
    WHERE creation_date >= '{START_DATE}'
      AND creation_date < DATE_TRUNC('month', NOW())
    GROUP BY 1, 2, 3
    ORDER BY 1, 2, 3
    """
    result = execute_metabase_query(instance="dora", caller=CALLER, sql=sql, database_id=2)
    if not result.success:
        raise RuntimeError(f"dora creations structures: {result.error}")
    return [
        rec(row["mois"], "dora",
            "Création structure, hors employeur solidaire",
            "Support", False,
            map_struct(row["typology"]), int(row["nombre_actes"]),
            departement=parse_dept(row["departement"]))
        for row in to_rows(result)
    ]


def fetch_dora_mises_a_jour_structures():
    """Mises à jour de structures Dora (hors employeurs solidaires)."""
    sql = f"""
    SELECT
        TO_CHAR(DATE_TRUNC('month', modification_date), 'YYYY-MM') AS mois,
        typology,
        COALESCE(department, 'Inconnu') AS departement,
        COUNT(*) AS nombre_actes
    FROM structures_structure
    WHERE modification_date IS NOT NULL
      AND modification_date > creation_date
      AND modification_date >= '{START_DATE}'
      AND modification_date < DATE_TRUNC('month', NOW())
    GROUP BY 1, 2, 3
    ORDER BY 1, 2, 3
    """
    result = execute_metabase_query(instance="dora", caller=CALLER, sql=sql, database_id=2)
    if not result.success:
        raise RuntimeError(f"dora mises a jour structures: {result.error}")
    return [
        rec(row["mois"], "dora",
            "Mise à jour d\u2019une structure d\u2019offre de service, hors employeur solidaire",
            "Support", False,
            map_struct(row["typology"]), int(row["nombre_actes"]),
            departement=parse_dept(row["departement"]))
        for row in to_rows(result)
    ]


def fetch_dora_recherches():
    """Recherches de service Dora (utilisateurs loggés avec structure connue)."""
    sql = f"""
    WITH user_struct AS (
        SELECT DISTINCT ON (u.id)
            u.id AS user_id,
            s.typology
        FROM public.users_user u
        JOIN public.structures_structuremember sm ON sm.user_id = u.id
        JOIN public.structures_structure s ON s.id = sm.structure_id
        WHERE s.typology IS NOT NULL AND s.typology != ''
        ORDER BY u.id
    )
    SELECT
        TO_CHAR(DATE_TRUNC('month', sv.date), 'YYYY-MM') AS mois,
        COALESCE(us.typology, '') AS typology,
        COALESCE(sv.department, 'Inconnu') AS departement,
        COUNT(*) AS nombre_actes
    FROM stats_searchview sv
    LEFT JOIN user_struct us ON us.user_id = sv.user_id
    WHERE sv.date >= '{START_DATE}'
      AND sv.date < DATE_TRUNC('month', NOW())
    GROUP BY 1, 2, 3
    ORDER BY 1, 2, 3
    """
    result = execute_metabase_query(
        instance="dora", caller=CALLER, sql=sql, database_id=2, timeout=120,
    )
    if not result.success:
        raise RuntimeError(f"dora recherches: {result.error}")
    return [
        rec(row["mois"], "dora", "Recherche de service",
            "Support", False,
            map_struct(row["typology"]), int(row["nombre_actes"]),
            departement=parse_dept(row["departement"]))
        for row in to_rows(result)
    ]


def fetch_monrecap():
    """Distribution et remplissage de carnets Mon Récap."""
    sql = """
    SELECT
        TO_CHAR(DATE_TRUNC('month', "Date d'expédition"), 'YYYY-MM') AS mois_expedition,
        "Type de structure",
        "Nom Departement",
        SUM("Nombre de Carnets") AS carnets
    FROM monrecap."Commandes"
    WHERE "Date d'expédition" IS NOT NULL
      AND "Date d'expédition" >= '2024-01-01'
      AND "Date d'expédition" < DATE_TRUNC('month', NOW())
    GROUP BY 1, 2, 3
    ORDER BY 1, 2, 3
    """
    result = execute_metabase_query(instance="stats", caller=CALLER, sql=sql, database_id=2)
    if not result.success:
        raise RuntimeError(f"monrecap: {result.error}")

    expeditions: dict[tuple, float] = {}
    for row in to_rows(result):
        ts = map_struct(row.get("Type de structure"))
        dept = parse_dept(row.get("Nom Departement"))
        key = (row["mois_expedition"], ts, dept)
        expeditions[key] = expeditions.get(key, 0) + int(row["carnets"])

    dist_by_key: dict[tuple, float] = defaultdict(float)
    fill_by_key: dict[tuple, float] = defaultdict(float)

    for (exp_mois, ts, dept), carnets in expeditions.items():
        exp_year, exp_month = int(exp_mois[:4]), int(exp_mois[5:7])
        for d in range(1, 11):
            m = exp_month + d - 1
            year = exp_year + (m - 1) // 12
            month = (m - 1) % 12 + 1
            dist_by_key[(f"{year:04d}-{month:02d}", ts, dept)] += carnets * 0.10
        for d in range(1, 7):
            active_frac = min(d / 10, 1) - min(max(d - 6, 0) / 10, 1)
            m = exp_month + d - 1
            year = exp_year + (m - 1) // 12
            month = (m - 1) % 12 + 1
            fill_by_key[(f"{year:04d}-{month:02d}", ts, dept)] += carnets * active_frac * 1.093

    rows = []
    for (mois, ts, dept), val in dist_by_key.items():
        if mois in MONTHS and round(val) > 0:
            rows.append(rec(mois, "monrecap", "Distribution carnet Mon Récap",
                            "Accompagnement", False, ts, round(val), departement=dept))
    for (mois, ts, dept), val in fill_by_key.items():
        if mois in MONTHS and round(val) > 0:
            rows.append(rec(mois, "monrecap", "Remplissage carnet Mon Récap",
                            "Support", False, ts, round(val), departement=dept))
    return rows


def fetch_marche():
    """Diffusions d'offre inclusive et mises à jour de fiches entreprise — Le Marché."""
    sql_tenders = f"""
    SELECT
        TO_CHAR(DATE_TRUNC('month', t.created_at), 'YYYY-MM') AS mois,
        (t.siae_count > 0) AS north_star,
        CASE u.kind
            WHEN 'SIAE' THEN 'SIAE'
            ELSE 'Autre'
        END AS type_structure,
        COALESCE(pp.department_code, 'Inconnu') AS departement,
        COUNT(*) AS nombre_actes
    FROM tenders_tender t
    LEFT JOIN users_user u ON u.id = t.author_id
    LEFT JOIN perimeters_perimeter pp ON pp.id = t.location_id
    WHERE t.kind IN ('TENDER', 'PROJ', 'QUOTE')
      AND t.status IN ('SUBMITTED', 'SENT')
      AND t.created_at >= '{START_DATE}'
      AND t.created_at < DATE_TRUNC('month', NOW())
    GROUP BY 1, 2, 3, 4
    ORDER BY 1, 2, 3, 4
    """
    sql_updates = f"""
    SELECT
        TO_CHAR(DATE_TRUNC('month', so.updated_at), 'YYYY-MM') AS mois,
        COALESCE(s.department, 'Inconnu') AS departement,
        COUNT(*) AS nombre_actes
    FROM siaes_siaeoffer so
    JOIN siaes_siae s ON s.id = so.siae_id
    WHERE so.updated_at >= '{START_DATE}'
      AND so.updated_at < DATE_TRUNC('month', NOW())
    GROUP BY 1, 2
    ORDER BY 1, 2
    """
    r1 = execute_metabase_query(instance="stats", caller=CALLER, sql=sql_tenders, database_id=6)
    if not r1.success:
        raise RuntimeError(f"marche tenders: {r1.error}")
    r2 = execute_metabase_query(instance="stats", caller=CALLER, sql=sql_updates, database_id=6)
    if not r2.success:
        raise RuntimeError(f"marche updates: {r2.error}")

    rows = [
        rec(row["mois"], "marche", "Diffusion d\u2019offre inclusive",
            "Support",
            bool(row["north_star"]), row["type_structure"], int(row["nombre_actes"]),
            departement=parse_dept(row["departement"]))
        for row in to_rows(r1)
    ]
    rows += [
        rec(row["mois"], "marche", "Mise à jour fiche entreprise",
            "Support", False, "SIAE", int(row["nombre_actes"]),
            departement=parse_dept(row["departement"]))
        for row in to_rows(r2)
    ]
    return rows


CONTEXTE_TYPE_STRUCTURE = {
    "france-travail": "FRANCE_TRAVAIL",
    "mes-aides-france-travail": "FRANCE_TRAVAIL",
    "pilotage-réunion-france-travail": "FRANCE_TRAVAIL",
    "les-emplois": "SIAE",
    "emplois-de-linclusion": "SIAE",
    "cd35": "CONSEIL_DEPARTEMENTAL",
    "cd80-widget": "CONSEIL_DEPARTEMENTAL",
    "hautespyrenees-widget": "CONSEIL_DEPARTEMENTAL",
    "worldline-parcoursrsa": "DELEGATAIRE_RSA",
    "monenfant": "CAF_MSA",
    "agefiph": "TS_SPECIALISES",
    "finess": "TS_SPECIALISES",
    "action-logement": "TS_HEBERGEMENT",
    "alhpi-widget": "TS_HEBERGEMENT",
    "association-entourage-widget": "TS_HEBERGEMENT",
    "rezosocial.com": "TS_HEBERGEMENT",
    "soliguide": "TS_HEBERGEMENT",
    "cfppa-widget": "E2C_EPIDE_AFPA",
    "ouvreboite-afpa-widget": "E2C_EPIDE_AFPA",
    "cscendoume-widget": "CCAS_CIAS",
    "mdemarseille-widget": "CCAS_CIAS",
    "mon-suivi-social-widget": "CCAS_CIAS",
    "pyramide-est-widget": "CCAS_CIAS",
}

TEST_CONTEXTES = {
    "emplois-demo-widget", "emplois-pentest-widget",
    "les-emplois-demo-2026-01", "les-emplois-review-app-2026-01",
}


def fetch_data_inclusion():
    """Actes métiers data·inclusion (recherche, MAJ structure, MAJ service)."""
    sql = f"""
    SELECT
        TO_CHAR(DATE_TRUNC('month', semaine), 'YYYY-MM') AS mois,
        "Type d'acte" AS type_acte,
        contexte_acte,
        COALESCE("Departement ok", 'Inconnu') AS departement,
        SUM("Nombre d'actes métier") AS nombre_actes
    FROM "stats_pdi-actes_metiers-data_inclusion"
    WHERE semaine >= '{START_DATE}'
    GROUP BY 1, 2, 3, 4
    ORDER BY 1, 2, 3, 4
    """
    result = execute_metabase_query(
        instance="datalake", caller=CALLER, sql=sql, database_id=2,
    )
    if not result.success:
        raise RuntimeError(f"data-inclusion: {result.error}")

    type_map = {
        "recherche": "Recherche data\u00b7inclusion",
        "mise à jour de structure":
            "Mise à jour d\u2019une structure d\u2019offre de service, hors employeur solidaire",
        "mise à jour de service":
            "Mise à jour offre de service, hors emploi solidaire",
    }
    rows = []
    for row in to_rows(result):
        if row["contexte_acte"] in TEST_CONTEXTES:
            continue
        label = type_map.get(row["type_acte"], row["type_acte"])
        n = int(row["nombre_actes"])
        if n > 0:
            type_structure = CONTEXTE_TYPE_STRUCTURE.get(row["contexte_acte"], "Autre")
            rows.append(rec(row["mois"], "data-inclusion", label,
                            "Support", False, type_structure, n,
                            departement=parse_dept(row["departement"])))
    return rows


def main():
    """Regenerate /app/data/interactive/actes-metier/data.json from all sources."""
    print("Fetching all actes métiers (v5)...")
    all_records = []

    fetchers = [
        ("RDV-i (invitations)", fetch_rdvi),
        ("Emplois candidatures", fetch_emplois_candidatures),
        ("Emplois fiches de poste", fetch_emplois_fiches),
        ("Emplois structures", fetch_emplois_structures),
        ("Emplois diagnostics", fetch_emplois_diagnostics),
        ("Emplois recherches offre (Matomo)", fetch_emplois_recherches),
        ("Emplois recherches service (Matomo)", fetch_emplois_recherches_service),
        ("GPS", fetch_gps),
        ("Dora orientations", fetch_dora_orientations),
        ("Dora iMER / intentions", fetch_dora_imer),
        ("Dora MAJ fiches service", fetch_dora_fiches),
        ("Dora créations services", fetch_dora_creations_services),
        ("Dora créations structures", fetch_dora_creations_structures),
        ("Dora MAJ structures", fetch_dora_mises_a_jour_structures),
        ("Dora recherches service", fetch_dora_recherches),
        ("Mon Récap", fetch_monrecap),
        ("Marché", fetch_marche),
        ("data·inclusion", fetch_data_inclusion),
    ]

    for name, fn in fetchers:
        try:
            rows = fn()
            print(f"  {name}: {len(rows)} records")
            all_records.extend(rows)
        except RuntimeError as exc:
            print(f"  {name}: ERROR — {exc}")

    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
        "consolidation_lag_days": 30,
        "period": f"{MONTHS[0]} – {MONTHS[-1]}",
        "records": all_records,
    }

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    total = sum(r["nombre_actes"] for r in all_records)
    print(f"\nWrote {len(all_records)} records ({total:,} actes) to {OUTPUT}")


if __name__ == "__main__":
    main()