"""
Master port registry for marine/shipping peril monitoring.
Each port auto-generates congestion and dwell-time triggers.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Port:
    id: str          # e.g. "port-sgp-jurong"
    name: str        # e.g. "Port of Singapore (Jurong)"
    city: str
    country: str
    lat: float       # port centre coordinates
    lon: float
    anchor_bbox: tuple[float, float, float, float]  # (lat_min, lon_min, lat_max, lon_max) anchorage area
    un_locode: str   # e.g. "SGSIN"
    tier: str        # "tier1" or "tier2"


# ──────────────────────────────────────────────────────────────
# TIER 1 — 10 major global ports with anchorage bounding boxes
# ──────────────────────────────────────────────────────────────
# Anchorage bboxes are approximate rectangles covering the main
# anchorage/waiting areas outside each port, where vessels queue.

GLOBAL_PORTS: list[Port] = [
    Port(
        id="port-singapore",
        name="Port of Singapore",
        city="Singapore",
        country="Singapore",
        lat=1.2650, lon=103.8200,
        anchor_bbox=(1.15, 103.70, 1.35, 104.00),  # Singapore Strait anchorage
        un_locode="SGSIN",
        tier="tier1",
    ),
    Port(
        id="port-rotterdam",
        name="Port of Rotterdam",
        city="Rotterdam",
        country="Netherlands",
        lat=51.9500, lon=4.1300,
        anchor_bbox=(51.90, 3.80, 52.05, 4.30),  # Maas anchorage / Hook of Holland
        un_locode="NLRTM",
        tier="tier1",
    ),
    Port(
        id="port-shanghai",
        name="Port of Shanghai (Yangshan)",
        city="Shanghai",
        country="China",
        lat=30.6300, lon=122.0700,
        anchor_bbox=(30.40, 121.80, 30.80, 122.40),  # Yangshan deepwater anchorage
        un_locode="CNSHA",
        tier="tier1",
    ),
    Port(
        id="port-los-angeles",
        name="Port of Los Angeles / Long Beach",
        city="Los Angeles",
        country="USA",
        lat=33.7400, lon=-118.2700,
        anchor_bbox=(33.60, -118.50, 33.85, -118.10),  # San Pedro Bay anchorage
        un_locode="USLAX",
        tier="tier1",
    ),
    Port(
        id="port-jnpt",
        name="Jawaharlal Nehru Port (JNPT)",
        city="Mumbai",
        country="India",
        lat=18.9500, lon=72.9500,
        anchor_bbox=(18.80, 72.75, 19.10, 73.10),  # Mumbai anchorage
        un_locode="INNSA",
        tier="tier1",
    ),
    Port(
        id="port-jebel-ali",
        name="Port of Jebel Ali",
        city="Dubai",
        country="UAE",
        lat=25.0100, lon=55.0600,
        anchor_bbox=(24.85, 54.85, 25.15, 55.25),  # Jebel Ali anchorage
        un_locode="AEJEA",
        tier="tier1",
    ),
    Port(
        id="port-hamburg",
        name="Port of Hamburg",
        city="Hamburg",
        country="Germany",
        lat=53.5400, lon=9.9700,
        anchor_bbox=(53.80, 8.50, 54.00, 9.00),  # Elbe estuary anchorage
        un_locode="DEHAM",
        tier="tier1",
    ),
    Port(
        id="port-colombo",
        name="Port of Colombo",
        city="Colombo",
        country="Sri Lanka",
        lat=6.9400, lon=79.8500,
        anchor_bbox=(6.80, 79.70, 7.05, 79.95),  # Colombo outer anchorage
        un_locode="LKCMB",
        tier="tier1",
    ),
    Port(
        id="port-klang",
        name="Port Klang",
        city="Port Klang",
        country="Malaysia",
        lat=2.9900, lon=101.3900,
        anchor_bbox=(2.85, 101.20, 3.10, 101.55),  # Strait of Malacca anchorage
        un_locode="MYPKG",
        tier="tier1",
    ),
    Port(
        id="port-busan",
        name="Port of Busan",
        city="Busan",
        country="South Korea",
        lat=35.1000, lon=129.0700,
        anchor_bbox=(34.95, 128.90, 35.15, 129.20),  # Busan outer anchorage
        un_locode="KRPUS",
        tier="tier1",
    ),
]


ALL_PORTS: list[Port] = GLOBAL_PORTS


def get_port_by_id(port_id: str) -> Port | None:
    return next((p for p in ALL_PORTS if p.id == port_id), None)


def get_port_by_locode(un_locode: str) -> Port | None:
    return next((p for p in ALL_PORTS if p.un_locode == un_locode), None)
