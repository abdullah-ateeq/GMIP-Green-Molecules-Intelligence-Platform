from __future__ import annotations

import os
import re
from typing import Any, Callable

import requests

from gmip.collectors.base import GmipCollector
from gmip.models.raw_document import RawDocument

RecordMapper = Callable[[dict[str, Any]], RawDocument | None]

REQUEST_TIMEOUT_SECONDS = 15

# Status codes handled explicitly (with a distinct log message) rather
# than falling through to the generic "unexpected status" branch.
_AUTH_FAILURE_CODES = {401, 403}


class LicensedSourceConnector(GmipCollector):
    """
    Base class for sources that require a licence/API credentials GMIP
    does not yet have real API documentation for.

    collect() only ever calls the network when BOTH `endpoint_env_var`
    and `credential_env_var` are set in the environment — it never
    scrapes the provider's public website, never bypasses auth/paywalls/
    robots.txt/rate limits, and never fabricates credentials. The
    endpoint URL always comes from the environment (the authorized
    endpoint the operator configures), never a hardcoded public-site URL.

    Because no official response schema exists yet for any of the four
    sources built on this base (see each subclass), a successful response
    is deliberately NOT parsed into guessed fields. Pass a `record_mapper`
    (dict -> RawDocument | None) once a source's real API documentation
    is available — everything else (auth, timeout, error handling,
    pagination-free single-page fetch) is already implemented and tested.
    """

    #: .env variable names holding the API endpoint and credential. Set
    #: by each concrete subclass.
    endpoint_env_var: str = ""
    credential_env_var: str = ""

    def __init__(
        self,
        source_definition,
        logger=None,
        record_mapper: RecordMapper | None = None,
    ) -> None:
        super().__init__(source_definition, logger=logger)
        self.record_mapper = record_mapper or self.default_record_mapper

    def collect(self) -> list[RawDocument]:
        endpoint, api_key = self._read_credentials()

        if not endpoint or not api_key:
            self.logger.info(
                "%s has no credentials configured (%s / %s) — "
                "skipping, source stays disabled.",
                self.collector_name,
                self.endpoint_env_var,
                self.credential_env_var,
            )
            return []

        try:
            response = requests.get(
                endpoint,
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=REQUEST_TIMEOUT_SECONDS,
            )

        except requests.Timeout:
            self.logger.warning(
                "%s request timed out after %ss.",
                self.collector_name,
                REQUEST_TIMEOUT_SECONDS,
            )
            return []

        except requests.RequestException as exc:
            # Covers connection errors, DNS failures, TLS errors, etc.
            # str(exc) is sanitized: requests' own exception messages can
            # otherwise repeat request details, so redact defensively.
            self.logger.warning(
                "%s request failed: %s",
                self.collector_name,
                self._redact(str(exc)),
            )
            return []

        return self._handle_response(response)

    def _handle_response(
        self,
        response: requests.Response,
    ) -> list[RawDocument]:
        if response.status_code in _AUTH_FAILURE_CODES:
            self.logger.warning(
                "%s authentication failed (HTTP %s) — check %s.",
                self.collector_name,
                response.status_code,
                self.credential_env_var,
            )
            return []

        if response.status_code == 404:
            self.logger.warning(
                "%s endpoint not found (HTTP 404) — check %s.",
                self.collector_name,
                self.endpoint_env_var,
            )
            return []

        if response.status_code == 429:
            self.logger.warning(
                "%s was rate-limited (HTTP 429).",
                self.collector_name,
            )
            return []

        if response.status_code >= 500:
            self.logger.warning(
                "%s reported a server error (HTTP %s).",
                self.collector_name,
                response.status_code,
            )
            return []

        if not response.ok:
            self.logger.warning(
                "%s returned an unexpected HTTP status: %s.",
                self.collector_name,
                response.status_code,
            )
            return []

        try:
            payload = response.json()
        except ValueError:
            self.logger.warning(
                "%s returned a response that was not valid JSON.",
                self.collector_name,
            )
            return []

        return self._map_records(payload)

    def _map_records(self, payload: Any) -> list[RawDocument]:
        raw_documents: list[RawDocument] = []

        for record in self._extract_records(payload):
            try:
                raw_document = self.record_mapper(record)
            except Exception as exc:
                self.logger.warning(
                    "%s failed to map one record, skipping it: %s",
                    self.collector_name,
                    self._redact(str(exc)),
                )
                continue

            if raw_document is not None:
                raw_documents.append(raw_document)

        return raw_documents

    @staticmethod
    def _extract_records(payload: Any) -> list[dict]:
        """
        Schema-agnostic record extraction: a bare JSON list, or a JSON
        object with a top-level list under one of a few common REST
        conventions. This is generic API shape, not a Hydrogen-Insight-
        specific (or any other provider's) assumption — anything else
        yields no records rather than guessing further.
        """
        if isinstance(payload, list):
            return [record for record in payload if isinstance(record, dict)]

        if isinstance(payload, dict):
            for key in ("data", "items", "results", "articles"):
                value = payload.get(key)

                if isinstance(value, list):
                    return [
                        record for record in value if isinstance(record, dict)
                    ]

        return []

    def default_record_mapper(
        self,
        record: dict[str, Any],
    ) -> RawDocument | None:
        """
        No confirmed API schema exists yet for this source — deliberately
        drops the record rather than guessing field names. Once the
        provider's official API documentation is available, either pass
        a real `record_mapper` to __init__, or override this method on
        the concrete subclass.
        """
        self.logger.info(
            "%s received a record but has no confirmed field mapping yet "
            "(pending official API documentation) — record skipped.",
            self.collector_name,
        )
        return None

    def _read_credentials(self) -> tuple[str | None, str | None]:
        return (
            os.environ.get(self.endpoint_env_var),
            os.environ.get(self.credential_env_var),
        )

    def _has_credentials(self) -> bool:
        endpoint, api_key = self._read_credentials()
        return bool(endpoint and api_key)

    @staticmethod
    def _redact(message: str) -> str:
        """Strip anything resembling a bearer token before it is logged."""
        return re.sub(r"Bearer\s+\S+", "Bearer <redacted>", message)

    def get_status(self) -> dict[str, object]:
        status = super().get_status()

        status["pending_reason"] = (
            "MISSING_CREDENTIALS"
            if not self._has_credentials()
            else "AWAITING_API_SCHEMA"
        )

        return status


class HydrogenInsightConnector(LicensedSourceConnector):
    """
    Hydrogen Insight (hydrogeninsight.com) explicitly names and disallows
    AI/LLM crawlers in its robots.txt. This connector never touches the
    public website — see LicensedSourceConnector's docstring.

    STATUS: no official Hydrogen Insight API/feed endpoint or response
    schema documentation is available yet. Until it is, every record
    from a (hypothetically configured) endpoint is dropped rather than
    mapped with guessed field names — pass a real `record_mapper` (or
    override `default_record_mapper`) once that documentation exists.
    """

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
