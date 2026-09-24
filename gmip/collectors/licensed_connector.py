from __future__ import annotations

import os

from gmip.collectors.base import GmipCollector
from gmip.models.raw_document import RawDocument


class LicensedSourceConnector(GmipCollector):
    """
    Base class for sources that require a licence/API credentials GMIP does
    not yet have.

    collect() always returns an empty list. There is deliberately no HTTP or
    API request code anywhere in this class or its subclasses below — it is
    structurally impossible for it to scrape a restricted public site or
    call an API without real credentials, per the phase brief's "do not
    fake data access" rule. Once the required .env variables are supplied,
    a real request implementation replaces the body of collect() — the
    calling contract (collect() -> list[RawDocument]) does not change.
    """

    #: Subclasses set this to the .env variable name holding the API/feed
    #: endpoint, and this to the variable holding the credential/key.
    endpoint_env_var: str = ""
    credential_env_var: str = ""

    def collect(self) -> list[RawDocument]:
        if not self._has_credentials():
            self.logger.info(
                "%s has no credentials configured (%s / %s) — "
                "skipping, source stays disabled.",
                self.collector_name,
                self.endpoint_env_var,
                self.credential_env_var,
            )
            return []

        # Credentials exist but no request implementation has been written
        # yet for this source. This is intentional: building the real
        # request logic is out of scope until the actual API/feed contract
        # for this source is known.
        self.logger.warning(
            "%s has credentials configured but no request implementation "
            "yet — returning no documents.",
            self.collector_name,
        )
        return []

    def _has_credentials(self) -> bool:
        return bool(
            os.environ.get(self.endpoint_env_var)
            and os.environ.get(self.credential_env_var)
        )

    def get_status(self) -> dict[str, object]:
        status = super().get_status()

        status["pending_reason"] = (
            "MISSING_CREDENTIALS"
            if not self._has_credentials()
            else "CREDENTIALS_SET_NO_IMPLEMENTATION"
        )

        return status


class HydrogenInsightConnector(LicensedSourceConnector):
    collector_id = "hydrogen_insight"
    collector_name = "Hydrogen Insight"
    endpoint_env_var = "HYDROGEN_INSIGHT_API_URL"
    credential_env_var = "HYDROGEN_INSIGHT_API_KEY"


class RechargeNewsConnector(LicensedSourceConnector):
    collector_id = "recharge_news"
    collector_name = "Recharge News"
    endpoint_env_var = "RECHARGE_NEWS_API_URL"
    credential_env_var = "RECHARGE_NEWS_API_KEY"


class SPGlobalConnector(LicensedSourceConnector):
    collector_id = "sp_global_commodity_insights"
    collector_name = "S&P Global Commodity Insights"
    endpoint_env_var = "SP_GLOBAL_API_URL"
    credential_env_var = "SP_GLOBAL_API_KEY"


class ArgusConnector(LicensedSourceConnector):
    collector_id = "argus_media"
    collector_name = "Argus Media"
    endpoint_env_var = "ARGUS_API_URL"
    credential_env_var = "ARGUS_API_KEY"
