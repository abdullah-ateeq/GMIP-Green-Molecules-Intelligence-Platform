from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gmip.provenance import check_url_availability  # noqa: E402


def _response(status_code: int, final_url: str) -> MagicMock:
    response = MagicMock(spec=requests.Response)
    response.status_code = status_code
    response.url = final_url
    return response


def test_valid_200_article_is_available() -> None:
    with patch(
        "gmip.provenance.requests.head",
        return_value=_response(200, "https://example.test/story/real/1.article/"),
    ):
        result = check_url_availability(
            "https://example.test/story/real/1.article/"
        )

    assert result["available"] is True
    assert result["status"] == "AVAILABLE"
    assert result["http_status"] == 200


def test_redirect_reports_final_url() -> None:
    with patch(
        "gmip.provenance.requests.head",
        return_value=_response(200, "https://example.test/story/real/1-renamed.article/"),
    ):
        result = check_url_availability(
            "https://example.test/story/real/1.article/"
        )

    assert result["available"] is True
    assert result["final_url"] == "https://example.test/story/real/1-renamed.article/"


def test_404_is_unavailable() -> None:
    with patch(
        "gmip.provenance.requests.head",
        return_value=_response(404, "https://example.test/story/gone/1.article/"),
    ):
        result = check_url_availability(
            "https://example.test/story/gone/1.article/"
        )

    assert result["available"] is False
    assert result["status"] == "UNAVAILABLE"
    assert result["http_status"] == 404


def test_410_gone_is_unavailable() -> None:
    with patch(
        "gmip.provenance.requests.head",
        return_value=_response(410, "https://example.test/story/removed/1.article/"),
    ):
        result = check_url_availability(
            "https://example.test/story/removed/1.article/"
        )

    assert result["available"] is False
    assert result["status"] == "UNAVAILABLE"


def test_blocked_403_is_unverified_not_unavailable() -> None:
    """
    A site blocking automated requests is not the same as the resource
    being gone — must never be reported as UNAVAILABLE.
    """
    with patch(
        "gmip.provenance.requests.head",
        return_value=_response(403, "https://example.test/story/real/1.article/"),
    ):
        result = check_url_availability(
            "https://example.test/story/real/1.article/"
        )

    assert result["available"] is None
    assert result["status"] == "UNVERIFIED"
    assert result["http_status"] == 403


def test_connection_error_is_unverified_without_crashing() -> None:
    with patch(
        "gmip.provenance.requests.head",
        side_effect=requests.ConnectionError("connection refused"),
    ):
        result = check_url_availability("https://example.test/story/real/1.article/")

    assert result["available"] is None
    assert result["status"] == "UNVERIFIED"
    assert result["http_status"] is None


def test_timeout_is_unverified_without_crashing() -> None:
    with patch(
        "gmip.provenance.requests.head",
        side_effect=requests.Timeout("timed out"),
    ):
        result = check_url_availability("https://example.test/story/real/1.article/")

    assert result["available"] is None
    assert result["status"] == "UNVERIFIED"


def test_head_not_allowed_falls_back_to_get() -> None:
    with patch(
        "gmip.provenance.requests.head",
        return_value=_response(405, "https://example.test/story/real/1.article/"),
    ):
        with patch(
            "gmip.provenance.requests.get",
            return_value=_response(200, "https://example.test/story/real/1.article/"),
        ) as mock_get:
            result = check_url_availability(
                "https://example.test/story/real/1.article/"
            )

    mock_get.assert_called_once()
    assert result["available"] is True
    assert result["status"] == "AVAILABLE"
