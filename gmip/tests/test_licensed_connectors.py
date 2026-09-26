from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest
import requests

from gmip.collectors import (
    ArgusConnector,
    HydrogenInsightConnector,
    RechargeNewsConnector,
    SPGlobalConnector,
)
from gmip.config import get_source_definition
from gmip.models.raw_document import RawDocument

CONNECTOR_CASES = [
    (HydrogenInsightConnector, "hydrogen_insight"),
    (RechargeNewsConnector, "recharge_news"),
    (SPGlobalConnector, "sp_global_commodity_insights"),
    (ArgusConnector, "argus_media"),
]

FAKE_API_KEY = "sk-super-secret-test-key-should-never-be-logged"


def _set_credentials(connector_cls, monkeypatch, url="https://api.example-licensed.test/v1/articles"):
    monkeypatch.setenv(connector_cls.endpoint_env_var, url)
    monkeypatch.setenv(connector_cls.credential_env_var, FAKE_API_KEY)


def _response(status_code: int, json_data=None, json_error: bool = False) -> MagicMock:
    response = MagicMock(spec=requests.Response)
    response.status_code = status_code
    response.ok = 200 <= status_code < 300

    if json_error:
        response.json.side_effect = ValueError("Expecting value")
    else:
        response.json.return_value = json_data if json_data is not None else []

    return response


@pytest.mark.parametrize("connector_cls, source_id", CONNECTOR_CASES)
def test_missing_credentials_collects_nothing(
    connector_cls, source_id, monkeypatch,
) -> None:
    monkeypatch.delenv(connector_cls.endpoint_env_var, raising=False)
    monkeypatch.delenv(connector_cls.credential_env_var, raising=False)

    connector = connector_cls(get_source_definition(source_id))

    assert connector.collect() == []
    assert connector.get_status()["pending_reason"] == "MISSING_CREDENTIALS"


@pytest.mark.parametrize("connector_cls, source_id", CONNECTOR_CASES)
def test_partial_credentials_collects_nothing(
    connector_cls, source_id, monkeypatch,
) -> None:
    """Only one of the two required env vars set — still must not request."""
    monkeypatch.setenv(connector_cls.endpoint_env_var, "https://api.example.test/")
    monkeypatch.delenv(connector_cls.credential_env_var, raising=False)

    connector = connector_cls(get_source_definition(source_id))

    with patch("gmip.collectors.licensed_connector.requests.get") as mock_get:
        assert connector.collect() == []
        mock_get.assert_not_called()


def test_unauthorized_response_returns_empty(monkeypatch) -> None:
    _set_credentials(HydrogenInsightConnector, monkeypatch)
    connector = HydrogenInsightConnector(get_source_definition("hydrogen_insight"))

    with patch(
        "gmip.collectors.licensed_connector.requests.get",
        return_value=_response(401),
    ):
        assert connector.collect() == []

    status = connector.get_status()
    assert status["pending_reason"] == "AWAITING_API_SCHEMA"


def test_forbidden_response_returns_empty(monkeypatch) -> None:
    _set_credentials(HydrogenInsightConnector, monkeypatch)
    connector = HydrogenInsightConnector(get_source_definition("hydrogen_insight"))

    with patch(
        "gmip.collectors.licensed_connector.requests.get",
        return_value=_response(403),
    ):
        assert connector.collect() == []


def test_not_found_response_returns_empty(monkeypatch) -> None:
    _set_credentials(HydrogenInsightConnector, monkeypatch)
    connector = HydrogenInsightConnector(get_source_definition("hydrogen_insight"))

    with patch(
        "gmip.collectors.licensed_connector.requests.get",
        return_value=_response(404),
    ):
        assert connector.collect() == []


def test_rate_limited_response_returns_empty(monkeypatch) -> None:
    _set_credentials(HydrogenInsightConnector, monkeypatch)
    connector = HydrogenInsightConnector(get_source_definition("hydrogen_insight"))

    with patch(
        "gmip.collectors.licensed_connector.requests.get",
        return_value=_response(429),
    ):
        assert connector.collect() == []


def test_server_error_response_returns_empty(monkeypatch) -> None:
    _set_credentials(HydrogenInsightConnector, monkeypatch)
    connector = HydrogenInsightConnector(get_source_definition("hydrogen_insight"))

    with patch(
        "gmip.collectors.licensed_connector.requests.get",
        return_value=_response(503),
    ):
        assert connector.collect() == []


def test_connection_error_returns_empty_without_crashing(monkeypatch) -> None:
    _set_credentials(HydrogenInsightConnector, monkeypatch)
    connector = HydrogenInsightConnector(get_source_definition("hydrogen_insight"))

    with patch(
        "gmip.collectors.licensed_connector.requests.get",
        side_effect=requests.ConnectionError("connection refused"),
    ):
        assert connector.collect() == []


def test_timeout_returns_empty_without_crashing(monkeypatch) -> None:
    _set_credentials(HydrogenInsightConnector, monkeypatch)
    connector = HydrogenInsightConnector(get_source_definition("hydrogen_insight"))

    with patch(
        "gmip.collectors.licensed_connector.requests.get",
        side_effect=requests.Timeout("timed out"),
    ):
        assert connector.collect() == []


def test_malformed_json_returns_empty(monkeypatch) -> None:
    _set_credentials(HydrogenInsightConnector, monkeypatch)
    connector = HydrogenInsightConnector(get_source_definition("hydrogen_insight"))

    with patch(
        "gmip.collectors.licensed_connector.requests.get",
        return_value=_response(200, json_error=True),
    ):
        assert connector.collect() == []


def test_valid_response_without_mapper_drops_records_conservatively(
    monkeypatch,
) -> None:
    """
    No official schema exists yet, so even a syntactically valid,
    authorized response yields zero RawDocuments by default — this is
    intentional (see LicensedSourceConnector's docstring), not a bug.
    """
    _set_credentials(HydrogenInsightConnector, monkeypatch)
    connector = HydrogenInsightConnector(get_source_definition("hydrogen_insight"))

    fake_payload = {
        "data": [
            {"headline": "Some article", "link": "https://example.test/a"},
        ],
    }

    with patch(
        "gmip.collectors.licensed_connector.requests.get",
        return_value=_response(200, json_data=fake_payload),
    ):
        assert connector.collect() == []


def test_valid_response_with_injected_mapper_converts_to_raw_documents(
    monkeypatch,
) -> None:
    """
    Proves the request/auth/error-handling/record-extraction plumbing is
    fully wired end-to-end: once a real record_mapper exists (built from
    the provider's actual API docs), records flow through to RawDocument
    correctly. Uses a test-only mapper — production code ships no guessed
    field names (see default_record_mapper).
    """
    _set_credentials(HydrogenInsightConnector, monkeypatch)

    def mapper(record: dict) -> RawDocument:
        return RawDocument(
            source_id="hydrogen_insight",
            source_name="Hydrogen Insight",
            source_url=record["link"],
            title=record["headline"],
            text=record.get("summary"),
        )

    connector = HydrogenInsightConnector(
        get_source_definition("hydrogen_insight"),
        record_mapper=mapper,
    )

    fake_payload = {
        "data": [
            {
                "headline": "Green ammonia project reaches FID",
                "link": "https://api.example-licensed.test/articles/123",
                "summary": "A project reached FID this week.",
            },
        ],
    }

    with patch(
        "gmip.collectors.licensed_connector.requests.get",
        return_value=_response(200, json_data=fake_payload),
    ):
        documents = connector.collect()

    assert len(documents) == 1
    assert documents[0].title == "Green ammonia project reaches FID"
    assert documents[0].source_url == (
        "https://api.example-licensed.test/articles/123"
    )
    assert documents[0].source_id == "hydrogen_insight"


def test_mapper_exception_skips_only_that_record(monkeypatch) -> None:
    _set_credentials(HydrogenInsightConnector, monkeypatch)

    def flaky_mapper(record: dict) -> RawDocument | None:
        if record["id"] == "bad":
            raise KeyError("missing field")

        return RawDocument(
            source_id="hydrogen_insight",
            source_name="Hydrogen Insight",
            source_url="https://api.example-licensed.test/articles/good",
            title="Good record",
        )

    connector = HydrogenInsightConnector(
        get_source_definition("hydrogen_insight"),
        record_mapper=flaky_mapper,
    )

    fake_payload = {"data": [{"id": "bad"}, {"id": "good"}]}

    with patch(
        "gmip.collectors.licensed_connector.requests.get",
        return_value=_response(200, json_data=fake_payload),
    ):
        documents = connector.collect()

    assert len(documents) == 1
    assert documents[0].title == "Good record"


@pytest.mark.parametrize("connector_cls, source_id", CONNECTOR_CASES)
def test_request_only_ever_targets_configured_endpoint_not_public_site(
    connector_cls, source_id, monkeypatch,
) -> None:
    """
    Structural guard: the request must go to the operator-configured
    endpoint only — never a hardcoded URL on the provider's own public
    website, no matter what that endpoint is set to.
    """
    configured_url = "https://api.example-licensed.test/v1/feed"
    _set_credentials(connector_cls, monkeypatch, url=configured_url)
    connector = connector_cls(get_source_definition(source_id))

    with patch(
        "gmip.collectors.licensed_connector.requests.get",
        return_value=_response(200, json_data=[]),
    ) as mock_get:
        connector.collect()

    mock_get.assert_called_once()
    called_url = mock_get.call_args.args[0]
    assert called_url == configured_url
    assert called_url != connector.source_definition.base_url


def test_no_secret_values_appear_in_logs_on_failure(monkeypatch, caplog) -> None:
    _set_credentials(HydrogenInsightConnector, monkeypatch)
    connector = HydrogenInsightConnector(get_source_definition("hydrogen_insight"))

    # An exception message that itself happens to echo the Authorization
    # header, as some HTTP client internals do — must still be redacted.
    leaky_exception = requests.ConnectionError(
        f"Failed for request with headers "
        f"{{'Authorization': 'Bearer {FAKE_API_KEY}'}}"
    )

    with caplog.at_level(logging.DEBUG):
        with patch(
            "gmip.collectors.licensed_connector.requests.get",
            side_effect=leaky_exception,
        ):
            connector.collect()

    for record in caplog.records:
        assert FAKE_API_KEY not in record.getMessage()


@pytest.mark.parametrize("connector_cls, source_id", CONNECTOR_CASES)
def test_no_secret_values_appear_in_logs_on_success(
    connector_cls, source_id, monkeypatch, caplog,
) -> None:
    _set_credentials(connector_cls, monkeypatch)
    connector = connector_cls(get_source_definition(source_id))

    with caplog.at_level(logging.DEBUG):
        with patch(
            "gmip.collectors.licensed_connector.requests.get",
            return_value=_response(200, json_data={"data": [{"x": 1}]}),
        ):
            connector.collect()

    for record in caplog.records:
        assert FAKE_API_KEY not in record.getMessage()
