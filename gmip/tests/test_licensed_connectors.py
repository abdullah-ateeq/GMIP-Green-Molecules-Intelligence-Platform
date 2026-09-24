from __future__ import annotations

import pytest

from gmip.collectors import (
    ArgusConnector,
    HydrogenInsightConnector,
    RechargeNewsConnector,
    SPGlobalConnector,
)
from gmip.config import get_source_definition

CONNECTOR_CASES = [
    (HydrogenInsightConnector, "hydrogen_insight"),
    (RechargeNewsConnector, "recharge_news"),
    (SPGlobalConnector, "sp_global_commodity_insights"),
    (ArgusConnector, "argus_media"),
]


@pytest.mark.parametrize("connector_cls, source_id", CONNECTOR_CASES)
def test_licensed_connector_collects_nothing_without_credentials(
    connector_cls,
    source_id,
    monkeypatch,
) -> None:
    monkeypatch.delenv(connector_cls.endpoint_env_var, raising=False)
    monkeypatch.delenv(connector_cls.credential_env_var, raising=False)

    connector = connector_cls(get_source_definition(source_id))

    assert connector.collect() == []
    assert connector.get_status()["pending_reason"] == "MISSING_CREDENTIALS"


@pytest.mark.parametrize("connector_cls, source_id", CONNECTOR_CASES)
def test_licensed_connector_never_imports_network_libraries(
    connector_cls,
    source_id,
) -> None:
    """
    Structural guard: the licensed connector module must not import any
    HTTP/network library, so it is impossible for it to make a live
    request no matter what collect() is called with.
    """
    import gmip.collectors.licensed_connector as module

    source_code = open(module.__file__, encoding="utf-8").read()

    for forbidden in ("import requests", "import httpx", "urlopen", "feedparser"):
        assert forbidden not in source_code
