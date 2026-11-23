import pytest

from lib.source_request import InvalidRequest, check_request

METHODS = {"list": (set(), {"limit"}), "get": ({"id"}, set())}


class SourceInvalidRequest(InvalidRequest):
    pass


def test_allowed_request_returns_its_params():
    assert check_request("Source", METHODS, "get", {"id": "a"}) == {"id": "a"}
    assert check_request("Source", METHODS, "list", None) == {}


@pytest.mark.parametrize(
    "method,params,expected",
    [
        ("delete", {}, "Valeurs : list, get"),
        (["list"], {}, "Valeurs : list, get"),
        ("list", ["limit"], "params doit être un objet"),
        ("list", {"offset": 1}, "Paramètres permis : limit"),
        ("get", {}, "paramètres manquants pour get : id"),
    ],
)
def test_refusal_says_what_is_allowed(method, params, expected):
    with pytest.raises(SourceInvalidRequest, match=expected):
        check_request("Source", METHODS, method, params, SourceInvalidRequest)
