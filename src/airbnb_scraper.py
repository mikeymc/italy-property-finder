# ABOUTME: Scrapes Airbnb search results to collect listing data and pricing.
# ABOUTME: Uses curl_cffi for browser impersonation, parses embedded JSON from search pages.

import base64
import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Optional

from curl_cffi import requests

logger = logging.getLogger(__name__)

AIRBNB_API_KEY = "d306zoyjsyarp7ifhu67rjxn52tv0t20"
REQUEST_DELAY_SECONDS = 2.0


@dataclass
class AirbnbListing:
    listing_id: Optional[str]
    title: str
    name: str
    nightly_rate: Optional[float]
    total_price: Optional[float] = None
    nights: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    bedrooms: Optional[int] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    is_guest_favorite: bool = False


def parse_nightly_rate(a11y_label: str) -> Optional[float]:
    """Extract nightly rate from accessibility label like '€504 for 5 nights'."""
    if not a11y_label:
        return None
    match = re.search(
        r"[\$€£]?([\d,]+(?:\.\d+)?)\s+(?:for|per)\s+(\d+)\s+night",
        a11y_label,
    )
    if not match:
        return None
    total = float(match.group(1).replace(",", ""))
    nights = int(match.group(2))
    return total / nights


def _parse_listing_id(encoded_id: str) -> Optional[str]:
    """Decode base64-encoded Airbnb listing ID."""
    if not encoded_id:
        return None
    try:
        decoded = base64.b64decode(encoded_id).decode("utf-8")
        return decoded.split(":")[-1] if ":" in decoded else decoded
    except Exception:
        return None


def _parse_rating(rating_str: str) -> tuple[Optional[float], Optional[int]]:
    """Parse '4.87 (299)' into (4.87, 299)."""
    if not rating_str:
        return None, None
    match = re.match(r"([\d.]+)\s*\((\d+)\)", rating_str)
    if match:
        return float(match.group(1)), int(match.group(2))
    return None, None


def _parse_bedrooms(structured_content: dict) -> Optional[int]:
    """Extract bedroom count from structuredContent."""
    for item in structured_content.get("primaryLine", []):
        body = item.get("body", "")
        match = re.search(r"(\d+)\s+bedroom", body)
        if match:
            return int(match.group(1))
    return None


def parse_search_results(raw_results: list[dict]) -> list[AirbnbListing]:
    """Parse raw Airbnb search result dicts into AirbnbListing objects."""
    listings = []
    for r in raw_results:
        # Price
        sdp = r.get("structuredDisplayPrice", {})
        primary = sdp.get("primaryLine", {})
        a11y = primary.get("accessibilityLabel", "")
        nightly = parse_nightly_rate(a11y)

        # Total price and nights
        total_price = None
        nights = None
        price_match = re.search(
            r"[\$€£]?([\d,]+(?:\.\d+)?)\s+(?:for|per)\s+(\d+)\s+night",
            a11y,
        )
        if price_match:
            total_price = float(price_match.group(1).replace(",", ""))
            nights = int(price_match.group(2))

        # Listing ID and location
        dsl = r.get("demandStayListing", {})
        listing_id = _parse_listing_id(dsl.get("id", ""))
        coord = dsl.get("location", {}).get("coordinate", {})

        # Rating
        rating, review_count = _parse_rating(r.get("avgRatingLocalized", ""))

        # Bedrooms
        bedrooms = _parse_bedrooms(r.get("structuredContent", {}))

        # Guest favorite badge
        is_guest_favorite = any(
            b.get("loggingContext", {}).get("badgeType") == "GUEST_FAVORITE"
            for b in r.get("badges", [])
        )

        listings.append(
            AirbnbListing(
                listing_id=listing_id,
                title=r.get("title", ""),
                name=r.get("nameLocalized", {}).get(
                    "localizedStringWithTranslationPreference", ""
                ),
                nightly_rate=nightly,
                total_price=total_price,
                nights=nights,
                latitude=coord.get("latitude"),
                longitude=coord.get("longitude"),
                bedrooms=bedrooms,
                rating=rating,
                review_count=review_count,
                is_guest_favorite=is_guest_favorite,
            )
        )
    return listings


def _extract_search_data(html: str) -> Optional[dict]:
    """Extract the embedded JSON data from an Airbnb search page."""
    match = re.search(
        r'id="data-deferred-state-0"[^>]*>(.+?)</script>', html, re.DOTALL
    )
    if not match:
        return None
    return json.loads(match.group(1))


def location_slug(query: str) -> str:
    """Convert a location query to Airbnb's URL path slug format.

    Airbnb uses double-dashes between location parts, not comma-space.
    'CHIETI, Italy' -> 'CHIETI--Italy'
    """
    parts = [p.strip() for p in query.split(",")]
    return "--".join(p for p in parts if p)


def search_listings(
    query: str,
    checkin: str,
    checkout: str,
    adults: int = 2,
    cursor: Optional[str] = None,
) -> tuple[list[AirbnbListing], Optional[str]]:
    """Search Airbnb for listings. Returns (listings, next_page_cursor)."""
    params = {
        "tab_id": "home_tab",
        "refinement_paths[]": "/homes",
        "room_types[]": "Entire home/apt",
        "query": query,
        "checkin": checkin,
        "checkout": checkout,
        "adults": adults,
        "price_filter_num_nights": 5,
    }
    if cursor:
        params["cursor"] = cursor

    resp = requests.get(
        f"https://www.airbnb.com/s/{location_slug(query)}/homes",
        params=params,
        impersonate="chrome",
        timeout=30,
    )

    if resp.status_code != 200:
        logger.warning("Airbnb search returned %d", resp.status_code)
        return [], None

    data = _extract_search_data(resp.text)
    if not data:
        logger.warning("Could not extract search data from response")
        return [], None

    try:
        stays = data["niobeClientData"][0][1]["data"]["presentation"]["staysSearch"]
        results = stays["results"]
        raw_listings = results["searchResults"]
        pagination = results.get("paginationInfo", {})
        next_cursor = pagination.get("nextPageCursor")
    except (KeyError, IndexError) as e:
        logger.warning("Unexpected data structure: %s", e)
        return [], None

    listings = parse_search_results(raw_listings)
    return listings, next_cursor


def build_bounds_params(
    ne_lat: float,
    ne_lng: float,
    sw_lat: float,
    sw_lng: float,
    checkin: str,
    checkout: str,
    adults: int = 2,
    cursor: Optional[str] = None,
) -> dict:
    """Build Airbnb search params for a geographic bounding box."""
    params = {
        "tab_id": "home_tab",
        "refinement_paths[]": "/homes",
        "room_types[]": "Entire home/apt",
        "checkin": checkin,
        "checkout": checkout,
        "adults": adults,
        "price_filter_num_nights": 5,
        "ne_lat": ne_lat,
        "ne_lng": ne_lng,
        "sw_lat": sw_lat,
        "sw_lng": sw_lng,
        "search_type": "user_map_move",
    }
    if cursor:
        params["cursor"] = cursor
    return params


def search_by_bounds(
    ne_lat: float,
    ne_lng: float,
    sw_lat: float,
    sw_lng: float,
    checkin: str,
    checkout: str,
    max_pages: int = 3,
    adults: int = 2,
) -> list[AirbnbListing]:
    """Search Airbnb listings within a bounding box. Returns all listings found."""
    all_listings = []
    cursor = None

    for page in range(max_pages):
        if page > 0:
            time.sleep(REQUEST_DELAY_SECONDS)

        params = build_bounds_params(
            ne_lat=ne_lat,
            ne_lng=ne_lng,
            sw_lat=sw_lat,
            sw_lng=sw_lng,
            checkin=checkin,
            checkout=checkout,
            adults=adults,
            cursor=cursor,
        )

        resp = requests.get(
            "https://www.airbnb.com/s/Italy/homes",
            params=params,
            impersonate="chrome",
            timeout=30,
        )

        if resp.status_code != 200:
            logger.warning("Airbnb bounds search returned %d", resp.status_code)
            break

        data = _extract_search_data(resp.text)
        if not data:
            logger.warning("Could not extract search data from bounds response")
            break

        try:
            stays = data["niobeClientData"][0][1]["data"]["presentation"]["staysSearch"]
            results = stays["results"]
            raw_listings = results["searchResults"]
            pagination = results.get("paginationInfo", {})
            next_cursor = pagination.get("nextPageCursor")
        except (KeyError, IndexError) as e:
            logger.warning("Unexpected data structure in bounds response: %s", e)
            break

        listings = parse_search_results(raw_listings)
        all_listings.extend(listings)
        logger.info(
            "Bounds page %d: found %d listings (total: %d)",
            page + 1,
            len(listings),
            len(all_listings),
        )

        if not next_cursor or not listings:
            break
        cursor = next_cursor

    return all_listings


def search_area(
    query: str,
    checkin: str,
    checkout: str,
    max_pages: int = 5,
    adults: int = 2,
) -> list[AirbnbListing]:
    """Search an area with pagination. Returns all listings found."""
    all_listings = []
    cursor = None

    for page in range(max_pages):
        if page > 0:
            time.sleep(REQUEST_DELAY_SECONDS)

        listings, next_cursor = search_listings(
            query, checkin, checkout, adults=adults, cursor=cursor
        )
        all_listings.extend(listings)
        logger.info(
            "Page %d: found %d listings (total: %d)",
            page + 1,
            len(listings),
            len(all_listings),
        )

        if not next_cursor or not listings:
            break
        cursor = next_cursor

    return all_listings
