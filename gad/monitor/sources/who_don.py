"""
WHO Disease Outbreak News (DON): free disease outbreak monitoring.
https://www.who.int/emergencies/disease-outbreak-news

Parses WHO DON RSS feed — no API key required.
Returns outbreak count matching the trigger's country within the last 7 days.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

import httpx

from gad.monitor.cache import write_cache

WHO_DON_RSS_URL = "https://www.who.int/feeds/entity/don/en/rss.xml"
TIMEOUT = 20

# Map trigger city names to their countries for matching
TRIGGER_COUNTRY_MAP = {
    "health-delhi": "India",
    "health-mumbai": "India",
    "health-lagos": "Nigeria",
    "health-dhaka": "Bangladesh",
    "health-jakarta": "Indonesia",
    "health-cairo": "Egypt",
    "health-kinshasa": "Democratic Republic of the Congo",
    "health-lima": "Peru",
    "health-bangkok": "Thailand",
    "health-nairobi": "Kenya",
}

# Alternative country name patterns that WHO might use
COUNTRY_ALIASES: dict[str, list[str]] = {
    "India": ["india"],
    "Nigeria": ["nigeria"],
    "Bangladesh": ["bangladesh"],
    "Indonesia": ["indonesia"],
    "Egypt": ["egypt"],
    "Democratic Republic of the Congo": [
        "democratic republic of the congo",
        "congo",
        "drc",
    ],
    "Peru": ["peru"],
    "Thailand": ["thailand"],
    "Kenya": ["kenya"],
}


def _parse_rss(xml_text: str) -> list[dict]:
    """Parse WHO DON RSS XML into a list of outbreak dicts."""
    outbreaks = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return outbreaks

    # RSS items are under channel/item
    channel = root.find("channel")
    if channel is None:
        return outbreaks

    for item in channel.findall("item"):
        title_el = item.find("title")
        link_el = item.find("link")
        pub_date_el = item.find("pubDate")

        title = title_el.text.strip() if title_el is not None and title_el.text else ""
        link = link_el.text.strip() if link_el is not None and link_el.text else ""
        pub_date_str = (
            pub_date_el.text.strip()
            if pub_date_el is not None and pub_date_el.text
            else ""
        )

        # Parse date — WHO RSS uses RFC 822 format
        pub_date = None
        for fmt in (
            "%a, %d %b %Y %H:%M:%S %z",
            "%a, %d %b %Y %H:%M:%S GMT",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%d",
        ):
            try:
                pub_date = datetime.strptime(pub_date_str, fmt)
                if pub_date.tzinfo is None:
                    pub_date = pub_date.replace(tzinfo=timezone.utc)
                break
            except ValueError:
                continue

        outbreaks.append(
            {
                "title": title,
                "link": link,
                "pub_date": pub_date,
                "pub_date_str": pub_date_str,
            }
        )

    return outbreaks


def _match_country(title: str, country: str) -> bool:
    """Check if an outbreak title mentions the given country."""
    title_lower = title.lower()

    # Direct country name match
    if country.lower() in title_lower:
        return True

    # Try aliases
    aliases = COUNTRY_ALIASES.get(country, [])
    for alias in aliases:
        if alias in title_lower:
            return True

    return False


def _get_country_for_trigger(trigger_id: str) -> str | None:
    """Look up the country for a given health trigger ID."""
    return TRIGGER_COUNTRY_MAP.get(trigger_id)


def fetch_outbreaks(lat: float, lon: float, trigger_id: str) -> dict | None:
    """
    Fetch WHO Disease Outbreak News and filter for the trigger's country.

    Returns dict with:
        outbreak_count: int — outbreaks matching country in last 7 days
        latest_outbreak_title: str | None
        latest_date: str | None
        total_global_outbreaks: int — all outbreaks in last 7 days
        source: str
    """
    country = _get_country_for_trigger(trigger_id)
    if not country:
        return None

    try:
        resp = httpx.get(WHO_DON_RSS_URL, timeout=TIMEOUT, follow_redirects=True)
        resp.raise_for_status()
        all_outbreaks = _parse_rss(resp.text)
    except Exception:
        return None

    # Filter to last 7 days
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    recent = [
        o for o in all_outbreaks if o.get("pub_date") and o["pub_date"] >= cutoff
    ]

    # Match outbreaks to this trigger's country
    matching = [o for o in recent if _match_country(o["title"], country)]

    # Sort by date descending
    matching.sort(key=lambda o: o.get("pub_date") or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

    latest_title = matching[0]["title"] if matching else None
    latest_date = (
        matching[0]["pub_date"].isoformat() if matching and matching[0].get("pub_date") else None
    )

    result = {
        "outbreak_count": len(matching),
        "latest_outbreak_title": latest_title,
        "latest_date": latest_date,
        "total_global_outbreaks": len(recent),
        "country": country,
        "source": "who_don",
        "lat": lat,
        "lon": lon,
    }

    write_cache("health", trigger_id, result, ttl_seconds=7200)  # 2hr TTL
    return result


def evaluate_trigger(data: dict, threshold: float) -> dict:
    """Evaluate a health/pandemic trigger. Fires when outbreak_count >= threshold."""
    count = data.get("outbreak_count")
    if count is None:
        return {"fired": False, "value": None, "status": "no_data"}

    fired = count >= threshold
    return {
        "fired": fired,
        "value": count,
        "threshold": threshold,
        "unit": "outbreaks",
        "status": "critical" if fired else "normal",
        "latest_outbreak": data.get("latest_outbreak_title"),
        "total_global": data.get("total_global_outbreaks"),
        "country": data.get("country"),
    }
