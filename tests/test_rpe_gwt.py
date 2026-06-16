from lib.rpe_gwt import (
    build_flowsview_payload,
    cube_dm_urls,
    extract_frame_ids,
    flowsview_header,
    parse_charts,
    parse_cube_dm,
)

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


FLOWS_DM = (
    "//OK[7,"
    '"/ddenterpriseapi/DDEnterpriseServlet?action\\u003DgenDocViewAD\\u0026chartType\\u003Dtablereport1-template'
    "\\u0026cubeURL\\u003D%2Fddenterpriseapi%2FDDEnterpriseServlet%3Fmethod%3DgetFile%26item%3Dhistory"
    "%252Fcommon%252Foutput%252F5f330f848938b405b3bbb01a57f3603a%252Fcube_dm_5f330f848938b405b3bbb01a57f3603a"
    "_1b7246ade2f30587533f9cee98c4d8f9_19e9313b2a3_1781049618000.js"
    '\\u0026cubeViewURL\\u003D%2Fddenterpriseapi%2FDDEnterpriseServlet%3Fmethod%3DgetFile",'
    '"some other string with no cubeURL",'
    "7]"
)


def test_cube_dm_urls_maps_cube_key_to_getfile_url():
    urls = cube_dm_urls(FLOWS_DM)
    assert set(urls) == {"5f330f848938b405b3bbb01a57f3603a"}  # cube_key = 1er hex (= clé du dossier output)
    url = urls["5f330f848938b405b3bbb01a57f3603a"]
    assert url.startswith("/ddenterpriseapi/DDEnterpriseServlet?method=getFile&item=history%2Fcommon%2Foutput")
    assert "cube_dm_5f330f848938b405b3bbb01a57f3603a_1b7246ade2f30587533f9cee98c4d8f9_" in url


CUBE_DM = (
    "var derivatedFunc={}; function cubeDataSet(dm) { "
    "dm.cubeName='Acc\\xE8s et pr\\xE9sence en emploi'; "
    "(function(){ var dim=dm.addDim(0,'C_TERRITOIRE_ID','Territoire'); dm.objName['C_TERRITOIRE_ID']=dim; "
    "dim.archived=false; dim.displayMode=0; dim.time=false; dim.nbMembers=363; dim.category='1. Territoire'; "
    "dim.captionDim='C_LBLTERRITOIRE'; dim.addCaptions([null]); dim.order=false; }()); "
    "(function(){ var dim=dm.addDim(1,'C_LBLREGION','C_LBLREGION'); dm.objName['C_LBLREGION']=dim; "
    "dim.archived=true; dim.time=false; dim.nbMembers=1; dim.captionDim='C_LBLREGION'; }()); "
    "(function(){ var dim=dm.addDim(2,'D_DATEENT','Date d\\'entr\\xE9e'); dm.objName['D_DATEENT']=dim; "
    "dim.time=true; dim.nbMembers=24; dim.category='2. Date'; dim.captionDim='C_LBLDATEENT'; }()); "
    "(function(){ var dim=dm.addDim(3,'DATMAJ','DATMAJ',0); dm.objName['DATMAJ']=dim; "
    "dim.time=true; dim.nbMembers=1; }()); "
    "var format=new Format(0,'',2,false); "
    "var meas=dm.addMeasure(11,'N_DELAIACCES',0,format,'D\\xE9lais d\\'acc\\xE8s'); meas.archived=true; meas.trend=0; }"
)


def test_parse_cube_dm_dim_after_a_measure_keeps_its_attributes():
    # Why: garde-fou — une mesure avant une dimension ne doit pas tronquer le bloc d'attributs de cette dim.
    js = (
        "function cubeDataSet(dm) { dm.cubeName='X'; "
        "(function(){ var dim=dm.addDim(0,'D1','Dim1'); dm.objName['D1']=dim; dim.time=false; dim.nbMembers=2; }()); "
        "var meas=dm.addMeasure(1,'M1',0,format,'Mes1'); meas.archived=true; "
        "(function(){ var dim=dm.addDim(1,'D2','Dim2'); dm.objName['D2']=dim; "
        "dim.time=true; dim.nbMembers=5; dim.category='2. Date'; dim.captionDim='C_LBL2'; }()); }"
    )
    dims = parse_cube_dm(js)["dimensions"]
    assert dims[1] == {
        "id": "D2",
        "name": "Dim2",
        "category": "2. Date",
        "caption_dim": "C_LBL2",
        "n_members": 5,
        "time": True,
    }


def test_parse_cube_dm_extracts_cube_name_and_decorated_dims():
    cat = parse_cube_dm(CUBE_DM)
    assert cat["cube_name"] == "Accès et présence en emploi"
    assert cat["dimensions"] == [
        {
            "id": "C_TERRITOIRE_ID",
            "name": "Territoire",
            "category": "1. Territoire",
            "caption_dim": "C_LBLTERRITOIRE",
            "n_members": 363,
            "time": False,
        },
        {
            "id": "C_LBLREGION",
            "name": "C_LBLREGION",
            "category": None,
            "caption_dim": "C_LBLREGION",
            "n_members": 1,
            "time": False,
        },
        {
            "id": "D_DATEENT",
            "name": "Date d'entrée",
            "category": "2. Date",
            "caption_dim": "C_LBLDATEENT",
            "n_members": 24,
            "time": True,
        },
        {  # 4-arg addDim(...,0) variant must still parse
            "id": "DATMAJ",
            "name": "DATMAJ",
            "category": None,
            "caption_dim": None,
            "n_members": 1,
            "time": True,
        },
    ]
