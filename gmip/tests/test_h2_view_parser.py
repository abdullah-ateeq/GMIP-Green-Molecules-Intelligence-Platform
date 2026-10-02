from __future__ import annotations

from gmip.intelligence.enums import ConfidenceLevel, IntelligenceType
from gmip.parsers.h2_view_parser import H2ViewParser

# A trimmed-down but structurally faithful reconstruction of
# gasworld.com/h2-view/'s real layout (verified live): each card is an
# <a href=".../story/<slug>/<id>.article/">Real headline</a>, followed by an
# optional "By <Author>" byline and summary, then "<Category> <date> <N> min
# read". Dates appear either as "<N> day(s) ago" or an absolute "DD Mon YYYY".
H2_VIEW_PAGE_HTML = """
<html><body>
<div class="signals-grid">
  <div class="card">
    <a href="https://www.gasworld.com/story/170-firms-urge-eu-to-preserve-binding-green-hydrogen-targets/2260432.article/">
      170 firms urge EU to preserve binding green hydrogen targets
    </a>
    By Connor Jack
    A group of 170 European energy sector firms has urged the European
    Commission to maintain the binding green hydrogen transport mandates.
    Hydrogen News 2 days ago 2 min read
  </div>
  <div class="card">
    <a href="https://www.gasworld.com/story/h2-mobility-extends-hydrogen-price-cuts/2260562.article/">
      H2 Mobility extends hydrogen price cuts to 15 more German refuelling sites
    </a>
    Mobility 1 day ago 2 min read
  </div>
  <div class="card">
    <a href="https://www.gasworld.com/story/masdar-leaves-omv-sole-project-owner/2260018.article/">
      Masdar leaves OMV sole project owner of 140MW green ammonia plant
    </a>
    By Connor Jack
    Austrian refiner OMV will continue to develop its green ammonia facility
    after ACWA Power left the development in Saudi Arabia.
    Hydrogen News 18 Sep 2026 2 min read
  </div>
  <a href="https://www.gasworld.com/email-communication-guidance/">Email &amp; communication guidance</a>
</div>
</body></html>
"""


def _raw_record(html: str | None = H2_VIEW_PAGE_HTML) -> dict:
    return {
        "title": "H2 View | gasworld",
        "source_url": "https://www.gasworld.com/h2-view/",
        "text": "1 H2 Mobility extends hydrogen price cuts Mobility 1 day ago 2 min read",
        "html": html,
        "collected_at": "2026-09-19T12:00:00+00:00",
    }


def test_can_parse_requires_title_and_url() -> None:
    parser = H2ViewParser()

    assert parser.can_parse(
        {"title": "Some title", "source_url": "https://example.com/"}
    ) is True

    assert parser.can_parse({"title": "Some title"}) is False
    assert parser.can_parse({"source_url": "https://example.com/"}) is False


def test_parse_extracts_one_object_per_real_card() -> None:
    parser = H2ViewParser()

    results = parser.parse(_raw_record())

    assert len(results) == 3

    titles = [item.title for item in results]
    assert (
        "170 firms urge EU to preserve binding green hydrogen targets"
        in titles
    )
    assert (
        "H2 Mobility extends hydrogen price cuts to 15 more German "
        "refuelling sites" in titles
    )


def test_card_gets_exact_article_url_not_the_hub_page() -> None:
    parser = H2ViewParser()

    results = parser.parse(_raw_record())

    urls = {item.title: item.source_url for item in results}
    assert urls["170 firms urge EU to preserve binding green hydrogen targets"] == (
        "https://www.gasworld.com/story/170-firms-urge-eu-to-preserve-binding-green-hydrogen-targets/2260432.article/"
    )


def test_card_category_and_relative_date_recovered() -> None:
    parser = H2ViewParser()

    results = parser.parse(_raw_record())
    by_title = {item.title: item for item in results}

    card = by_title["170 firms urge EU to preserve binding green hydrogen targets"]
    assert card.categories == ["Hydrogen News"]
    assert card.published_at is not None
    assert card.published_at.date().isoformat() == "2026-09-17"
    assert "170 European energy sector firms" in (card.summary or "")


def test_card_absolute_date_is_parsed() -> None:
    parser = H2ViewParser()

    results = parser.parse(_raw_record())
    by_title = {item.title: item for item in results}

    card = by_title[
        "Masdar leaves OMV sole project owner of 140MW green ammonia plant"
    ]
    assert card.published_at.date().isoformat() == "2026-09-18"


def test_card_without_byline_has_no_fabricated_summary() -> None:
    parser = H2ViewParser()

    results = parser.parse(_raw_record())
    by_title = {item.title: item for item in results}

    card = by_title[
        "H2 Mobility extends hydrogen price cuts to 15 more German "
        "refuelling sites"
    ]
    assert card.summary is None


def test_parse_extracts_known_products_countries_companies() -> None:
    parser = H2ViewParser()

    results = parser.parse(_raw_record())
    by_title = {item.title: item for item in results}

    card = by_title[
        "Masdar leaves OMV sole project owner of 140MW green ammonia plant"
    ]
    assert card.products == ["Green Ammonia"]
    assert card.countries == ["Saudi Arabia"]
    # "ACWA" (a confirmed alias) is also its own whole-word match inside
    # "ACWA Power" — both mentions are preserved and both resolve to the
    # same canonical company during entity resolution.
    assert card.companies == ["ACWA", "ACWA Power", "Masdar"]
    assert card.confidence == ConfidenceLevel.MEDIUM
    assert card.intelligence_type == IntelligenceType.NEWS
    assert card.parser_name == "H2ViewParser"
    assert card.source_organisation == "H2 View"


def test_no_html_produces_no_intelligence_object() -> None:
    """
    The landing page itself is discovery input only, never an
    IntelligenceObject on its own (access-resilience brief, section 8) —
    it's already collected as a RawDocument for change detection.
    """
    parser = H2ViewParser()

    raw_record = _raw_record(html=None)
    results = parser.parse(raw_record)

    assert results == []


def test_404_page_produces_no_intelligence_object() -> None:
    parser = H2ViewParser()
    raw_record = _raw_record(html=None)
    raw_record["title"] = "404 - Page Not Found | gasworld"
    raw_record["text"] = "The page you requested could not be found."

    results = parser.parse(raw_record)

    assert results == []


def test_html_with_no_matching_article_links_produces_no_intelligence_object() -> None:
    parser = H2ViewParser()

    raw_record = _raw_record(
        html="<html><body><p>No article cards here.</p></body></html>"
    )
    results = parser.parse(raw_record)

    assert results == []


def test_identity_key_based_on_article_id_survives_domain_migration() -> None:
    """
    Section 10-11 of the access-resilience brief: the same article must
    not become duplicate intelligence merely because H2 View's domain
    changed from h2-view.com to gasworld.com — both URL forms carry the
    same trailing numeric article ID, which becomes the identity_key.
    """
    parser = H2ViewParser()

    gasworld_html = """
    <html><body>
    <a href="https://www.gasworld.com/story/uniper-locks-in-e-saf/2260404.article/">
      Uniper locks in 40,000 tonnes of e-SAF
    </a>
    Mobility 3 days ago 1 min read
    </body></html>
    """
    legacy_html = """
    <html><body>
    <a href="https://www.h2-view.com/story/uniper-locks-in-e-saf-renamed/2260404.article/">
      Uniper locks in 40,000 tonnes of e-SAF
    </a>
    Mobility 3 days ago 1 min read
    </body></html>
    """

    gasworld_record = _raw_record(html=gasworld_html)
    legacy_record = _raw_record(html=legacy_html)

    gasworld_results = parser.parse(gasworld_record)
    legacy_results = parser.parse(legacy_record)

    assert len(gasworld_results) == 1
    assert len(legacy_results) == 1
    assert gasworld_results[0].identity_key == legacy_results[0].identity_key
    assert gasworld_results[0].identity_key == "h2_view:2260404"


def test_identity_key_falls_back_safely_without_article_id() -> None:
    parser = H2ViewParser()
    html = """
    <html><body>
    <a href="https://www.gasworld.com/story/example/not-numeric.article/">
      A feature page headline that is long enough to match
    </a>
    Mobility 1 day ago 1 min read
    </body></html>
    """
    raw_record = _raw_record(html=html)

    results = parser.parse(raw_record)

    assert len(results) == 1
    assert results[0].identity_key is not None
