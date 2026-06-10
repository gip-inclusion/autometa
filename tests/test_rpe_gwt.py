from lib.rpe_gwt import build_flowsview_payload, extract_frame_ids, flowsview_header, parse_charts

WALLET = (
    '//OK[0,1,2,["Page d\'acceuil - KPI","99b3241e","Parcours en entree","a6ca5f7d",'
    '"Entree en parcours","fba0c2c4f5e0987f8c5d1cdd5bba387a","short","8009cc6","NOTAHEX_ZZ",'
    '"deadbeef","public"],7]'
)
HEADER = [str(i) for i in range(1, 20)]  # 19 fixed header strings


def test_extract_frame_ids_keeps_6_to_8_hex_dedup_in_order():
    ids = extract_frame_ids(WALLET)
    assert ids == ["99b3241e", "a6ca5f7d", "8009cc6", "deadbeef"]


def test_build_flowsview_payload_structure():
    payload = build_flowsview_payload(["aaa111", "bbb222"], HEADER)
    parts = payload.split("|")
    assert parts[0] == "7" and parts[1] == "3"
    assert parts[2] == "21"
    assert "ItemIdentifier(public\\!aaa111\\!-1)" in parts
    assert "ItemIdentifier(public\\!bbb222\\!-1)" in parts
    assert payload.endswith("|2|20|21|0|1|0|")


def test_build_flowsview_payload_empty_list():
    payload = build_flowsview_payload([], HEADER)
    assert payload.split("|")[2] == "19"
    assert payload.endswith("|0|0|1|0|")


def test_flowsview_header_returns_19_strings():
    sample = "7|3|19|" + "|".join(HEADER) + "|1|2|3|"
    assert flowsview_header(sample) == HEADER


FLOWS = (
    "//OK[7,"
    '"Taux de recours reportea4f0ecdf31b0b23801090bd1dcb0fa0",'
    '"Measures\\n    - Nombre de recours\\nDimensions",'
    '"Taux de recours",'
    '"Pr\\u00e9sence report41411590ece8ef6af71423ca28d33218",'
    '"Measures\\n    - Acc\\u00e8s %\\n    - BRSA %\\nDimensions\\n    - C_TERRITOIRE_ID",'
    '"/ddenterpriseapi/DDEnterpriseServlet?action\\u003DgenDocViewAD",'
    '"Measures\\n    - Noise (%)\\nDimensions\\n    - D_DATEENT",'
    '"Taux de recours reportea4f0ecdf31b0b23801090bd1dcb0fa0",'
    '"Measures\\n    - Nombre de recours\\nDimensions",'
    "7]"
)


def test_parse_charts_extracts_clean_records():
    recs = parse_charts(FLOWS)
    assert recs == [
        {
            "chart_title": "Taux de recours",
            "cube_key": "ea4f0ecdf31b0b23801090bd1dcb0fa0",
            "measures_shown": ["Nombre de recours"],
            "dims_shown": [],
        },
        {
            "chart_title": "Présence",
            "cube_key": "41411590ece8ef6af71423ca28d33218",
            "measures_shown": ["Accès %", "BRSA %"],
            "dims_shown": ["C_TERRITOIRE_ID"],
        },
    ]


def test_parse_charts_rejects_url_titles():
    assert not any(r["chart_title"].startswith("/ddenterpriseapi") for r in parse_charts(FLOWS))
