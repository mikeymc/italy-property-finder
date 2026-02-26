# ABOUTME: Tests for the Airbnb search scraper that collects listing data and pricing.
# ABOUTME: Uses real Airbnb responses to validate parsing logic.

import json
import re
from unittest.mock import patch

import pytest

from src.airbnb_scraper import (
    parse_search_results,
    parse_nightly_rate,
    AirbnbListing,
)


# Minimal fixture mimicking the Airbnb search result structure
SAMPLE_SEARCH_RESULT = {
    "__typename": "StaysSearchResult",
    "avgRatingLocalized": "4.87 (299)",
    "title": "Loft in Syracuse",
    "subtitle": "Cozy place in Ortigia",
    "nameLocalized": {
        "__typename": "UGCText",
        "localizedStringWithTranslationPreference": "Cozy place in Ortigia",
    },
    "structuredDisplayPrice": {
        "primaryLine": {
            "accessibilityLabel": "\u20ac504 for 5 nights",
            "price": "\u20ac504",
            "qualifier": "for 5 nights",
        },
    },
    "structuredContent": {
        "primaryLine": [
            {"body": "1 bedroom", "type": "BEDINFO"},
            {"body": "1 bed", "type": "BEDINFO"},
        ],
        "secondaryLine": [
            {"body": "Mar 2\u2009\u2013\u20097", "type": "DATE"},
        ],
    },
    "demandStayListing": {
        "id": "RGVtYW5kU3RheUxpc3Rpbmc6NDM0MDUwOTM=",
        "location": {
            "coordinate": {
                "latitude": 37.05945,
                "longitude": 15.29731,
            },
        },
    },
    "badges": [
        {"text": "Guest favorite", "loggingContext": {"badgeType": "GUEST_FAVORITE"}},
    ],
}

SAMPLE_DISCOUNTED_RESULT = {
    "__typename": "StaysSearchResult",
    "avgRatingLocalized": "4.94 (33)",
    "title": "Apartment in Syracuse",
    "subtitle": "Discovery Ortigia",
    "nameLocalized": {
        "__typename": "UGCText",
        "localizedStringWithTranslationPreference": "Discovery Ortigia",
    },
    "structuredDisplayPrice": {
        "primaryLine": {
            "accessibilityLabel": "\u20ac254 for 5 nights, originally \u20ac294",
            "price": None,
            "qualifier": "for 5 nights",
        },
    },
    "structuredContent": {
        "primaryLine": [
            {"body": "2 bedrooms", "type": "BEDINFO"},
        ],
        "secondaryLine": [],
    },
    "demandStayListing": {
        "id": "RGVtYW5kU3RheUxpc3Rpbmc6MTQ2NzU3MjIzNjU4NzE4MDMzMw==",
        "location": {
            "coordinate": {
                "latitude": 37.0695,
                "longitude": 15.2882,
            },
        },
    },
    "badges": [],
}


class TestParseNightlyRate:
    def test_standard_price(self):
        assert parse_nightly_rate("\u20ac504 for 5 nights") == pytest.approx(100.8)

    def test_discounted_price(self):
        assert parse_nightly_rate("\u20ac254 for 5 nights, originally \u20ac294") == pytest.approx(50.8)

    def test_dollar_price(self):
        assert parse_nightly_rate("$300 for 3 nights") == pytest.approx(100.0)

    def test_with_commas(self):
        assert parse_nightly_rate("\u20ac1,200 for 5 nights") == pytest.approx(240.0)

    def test_no_match(self):
        assert parse_nightly_rate("Price unavailable") is None

    def test_empty(self):
        assert parse_nightly_rate("") is None


class TestParseSearchResults:
    def test_parses_listing_id(self):
        listings = parse_search_results([SAMPLE_SEARCH_RESULT])
        assert listings[0].listing_id == "43405093"

    def test_parses_title(self):
        listings = parse_search_results([SAMPLE_SEARCH_RESULT])
        assert listings[0].title == "Loft in Syracuse"

    def test_parses_name(self):
        listings = parse_search_results([SAMPLE_SEARCH_RESULT])
        assert listings[0].name == "Cozy place in Ortigia"

    def test_parses_nightly_rate(self):
        listings = parse_search_results([SAMPLE_SEARCH_RESULT])
        assert listings[0].nightly_rate == pytest.approx(100.8)

    def test_parses_coordinates(self):
        listings = parse_search_results([SAMPLE_SEARCH_RESULT])
        assert listings[0].latitude == pytest.approx(37.05945)
        assert listings[0].longitude == pytest.approx(15.29731)

    def test_parses_bedrooms(self):
        listings = parse_search_results([SAMPLE_SEARCH_RESULT])
        assert listings[0].bedrooms == 1

    def test_parses_rating(self):
        listings = parse_search_results([SAMPLE_SEARCH_RESULT])
        assert listings[0].rating == pytest.approx(4.87)
        assert listings[0].review_count == 299

    def test_parses_discounted_listing(self):
        listings = parse_search_results([SAMPLE_DISCOUNTED_RESULT])
        assert listings[0].nightly_rate == pytest.approx(50.8)
        assert listings[0].bedrooms == 2

    def test_parses_multiple_results(self):
        listings = parse_search_results([SAMPLE_SEARCH_RESULT, SAMPLE_DISCOUNTED_RESULT])
        assert len(listings) == 2

    def test_handles_missing_price(self):
        result = {**SAMPLE_SEARCH_RESULT}
        result["structuredDisplayPrice"] = {"primaryLine": {"accessibilityLabel": ""}}
        listings = parse_search_results([result])
        assert listings[0].nightly_rate is None

    def test_guest_favorite_badge(self):
        listings = parse_search_results([SAMPLE_SEARCH_RESULT])
        assert listings[0].is_guest_favorite is True

    def test_no_guest_favorite_badge(self):
        listings = parse_search_results([SAMPLE_DISCOUNTED_RESULT])
        assert listings[0].is_guest_favorite is False
