"""Client Datadog Logs — lib/datadog.py."""

import httpx
import pytest

from lib.datadog import BURST, RETENTION_DAYS, DatadogClient, DatadogError, RateLimiter, by_count, day_windows


def make_client(mocker, responses):
    client = DatadogClient(api_key="factice", app_key="factice", site="exemple.test")
    mocker.patch.object(client._session, "post", side_effect=responses)
    mocker.patch("lib.datadog.time.sleep")
    return client


def fake_response(status=200, payload=None):
    request = httpx.Request("POST", "https://api.exemple.test/")
    return httpx.Response(status, json=payload if payload is not None else {}, request=request)


def events_page(count, cursor=None):
    data = [
        {"attributes": {"timestamp": "2026-09-01T00:00:00Z", "attributes": {"http": {"url": f"/p/{i}"}}}}
        for i in range(count)
    ]
    return {"data": data, "meta": {"page": {"after": cursor} if cursor else {}}}


def test_the_client_refuses_to_start_without_both_keys():
    with pytest.raises(DatadogError, match="not set"):
        DatadogClient(api_key="factice", app_key=None, site="exemple.test")


def test_the_limiter_lets_the_burst_through_then_holds(mocker):
    clock = {"now": 0.0}
    mocker.patch("lib.datadog.time.monotonic", side_effect=lambda: clock["now"])
    sleep = mocker.patch(
        "lib.datadog.time.sleep", side_effect=lambda seconds: clock.__setitem__("now", clock["now"] + seconds)
    )
    limiter = RateLimiter(burst=2, window=10.0)

    limiter.acquire()
    limiter.acquire()
    assert sleep.call_count == 0

    # Why: la 3e demande doit attendre que la fenêtre glisse, sinon on repart en 429 en rafale.
    limiter.acquire()
    assert sleep.call_count == 1
    assert clock["now"] >= 10.0


@pytest.mark.parametrize("days", [1, 7, RETENTION_DAYS])
def test_day_windows_covers_the_requested_depth(days):
    windows = day_windows(days)
    assert len(windows) == days
    assert windows[0] == (f"now-{days}d", f"now-{days - 1}d")
    assert windows[-1] == ("now-1d", "now-0d")


def test_day_windows_refuses_to_ask_beyond_retention():
    with pytest.raises(DatadogError, match="30 jours"):
        day_windows(RETENTION_DAYS + 1)


def test_day_windows_groups_days_into_chunks():
    assert day_windows(10, chunk=5) == [("now-10d", "now-5d"), ("now-5d", "now-0d")]


@pytest.mark.parametrize("status", [408, 429, 503])
def test_a_throttled_call_is_retried_then_succeeds(mocker, status):
    client = make_client(mocker, [fake_response(status), fake_response(200, {"data": {"buckets": []}})])
    assert client.aggregate("service:x", "now-1d", "now") == []
    assert client._session.post.call_count == 2


def test_a_client_error_is_raised_rather_than_retried(mocker):
    client = make_client(mocker, [fake_response(403, {"errors": ["Forbidden"]})])
    with pytest.raises(DatadogError, match="HTTP 403"):
        client.count("service:x", "now-1d", "now")
    assert client._session.post.call_count == 1


def test_iter_events_follows_the_cursor_until_it_runs_out(mocker):
    client = make_client(mocker, [fake_response(200, events_page(2, "suite")), fake_response(200, events_page(1))])
    assert len(list(client.iter_events("service:x", "now-1d", "now"))) == 3


def test_iter_events_stops_at_the_requested_ceiling(mocker):
    client = make_client(mocker, [fake_response(200, events_page(5, "suite"))])
    assert len(list(client.iter_events("service:x", "now-1d", "now", max_events=3))) == 3


def test_count_reads_the_event_total_and_the_distinct_cardinality(mocker):
    payload = {"data": {"buckets": [{"computes": {"c0": 120, "c1": 7}}]}}
    client = make_client(mocker, [fake_response(200, payload)])
    assert client.count("service:x", "now-1d", "now", distinct="@usr.id") == {"count": 120, "distinct": 7}


def test_count_stays_zero_when_the_window_is_empty(mocker):
    client = make_client(mocker, [fake_response(200, {"data": {"buckets": []}})])
    assert client.count("service:x", "now-1d", "now") == {"count": 0, "distinct": None}


def test_the_burst_default_matches_the_measured_quota():
    """Le quota logs_public_search_api est de 3 requêtes par 10 s."""
    assert BURST == 3


def test_by_count_carries_the_measure_type_the_api_demands():
    """Sans `type: measure`, l'agrégation renvoie 400 et le tri retombe en ordre alphabétique."""
    assert by_count("@usr.kind", 5) == {
        "facet": "@usr.kind",
        "limit": 5,
        "sort": {"aggregation": "count", "order": "desc", "type": "measure"},
    }
