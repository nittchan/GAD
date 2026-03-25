# Parametric Data API Guide

## Overview

The Parametric Data API provides programmatic access to 521+ live parametric insurance triggers across 12 peril categories. Free, open, no authentication required by default.

Built by [Nitthin Chandran Nair](https://github.com/nittchan). Powered by [OrbitCover](https://orbitcover.com) (MedPiper Technologies — backed by Y Combinator).

## Base URL

- **Production:** `https://parametricdata.io:8502/v1`
- **Swagger UI:** `https://parametricdata.io:8502/v1/docs`
- **ReDoc:** `https://parametricdata.io:8502/v1/redoc`
- **OpenAPI spec:** `https://parametricdata.io:8502/v1/openapi.json`

## Authentication

Open by default. API key auth is opt-in for rate limiting:

- **Header:** `X-API-Key: your-api-key`
- Enable server-side with `API_REQUIRE_AUTH=true` environment variable.

When auth is disabled (default), all endpoints are fully public. When enabled, requests without a valid `X-API-Key` header receive a `401` response.

## Quick Start

```bash
# List all triggers
curl https://parametricdata.io:8502/v1/triggers

# Get a specific trigger
curl https://parametricdata.io:8502/v1/triggers/flight-delay-del

# Filter by peril
curl https://parametricdata.io:8502/v1/triggers?peril=earthquake

# Get basis risk report
curl https://parametricdata.io:8502/v1/triggers/weather-heat-del/basis-risk

# Get oracle determinations
curl https://parametricdata.io:8502/v1/triggers/flight-delay-del/determinations

# Check platform status
curl https://parametricdata.io:8502/v1/status

# List all peril categories
curl https://parametricdata.io:8502/v1/perils

# List marine ports
curl https://parametricdata.io:8502/v1/ports
```

## Endpoints

### List Triggers

```
GET /v1/triggers
```

List all parametric insurance triggers with their current cached status. Optionally filter by peril type.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|------|----------|-------------|
| `peril` | query | string | No | Filter by peril type (e.g. `earthquake`, `flood`, `flight_delay`) |

**Example request:**

```bash
curl https://parametricdata.io:8502/v1/triggers?peril=earthquake
```

**Example response:**

```json
{
  "triggers": [
    {
      "id": "earthquake-tokyo",
      "name": "Earthquake — Tokyo",
      "peril": "earthquake",
      "lat": 35.6762,
      "lon": 139.6503,
      "location_label": "Tokyo, Japan",
      "threshold": 5.0,
      "threshold_unit": "magnitude",
      "data_source": "usgs",
      "has_data": true,
      "is_stale": false
    }
  ],
  "count": 10
}
```

---

### Get Trigger

```
GET /v1/triggers/{trigger_id}
```

Get a single trigger with its full profile including cached data and threshold direction.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|------|----------|-------------|
| `trigger_id` | path | string | Yes | Trigger identifier (e.g. `flight-delay-del`) |

**Example request:**

```bash
curl https://parametricdata.io:8502/v1/triggers/flight-delay-del
```

**Example response:**

```json
{
  "id": "flight-delay-del",
  "name": "Flight Delay — DEL",
  "peril": "flight_delay",
  "peril_label": "Flight Delay",
  "lat": 28.5562,
  "lon": 77.1,
  "location_label": "Delhi (DEL), India",
  "threshold": 30.0,
  "threshold_unit": "% delayed",
  "fires_when_above": true,
  "data_source": "opensky",
  "description": "Fires when >30% of departures from DEL are delayed by 15+ minutes.",
  "cached_data": { "value": 12.5, "timestamp": "2026-03-25T10:00:00Z" },
  "is_stale": false
}
```

---

### Get Basis Risk Report

```
GET /v1/triggers/{trigger_id}/basis-risk
```

Get the precomputed basis risk report for a trigger. The report includes Spearman correlation, confidence interval, false positive/negative rates, and Lloyd's alignment score.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|------|----------|-------------|
| `trigger_id` | path | string | Yes | Trigger identifier |

**Example request:**

```bash
curl https://parametricdata.io:8502/v1/triggers/weather-heat-del/basis-risk
```

**Example response:**

```json
{
  "trigger_id": "weather-heat-del",
  "report": {
    "spearman_rho": 0.87,
    "confidence_interval": [0.82, 0.91],
    "p_value": 0.0001,
    "fpr": 0.05,
    "fnr": 0.08,
    "lloyds_score": 85,
    "periods_analysed": 365
  }
}
```

---

### Get Oracle Determinations

```
GET /v1/triggers/{trigger_id}/determinations
```

Get recent cryptographically signed oracle determinations for a trigger. Determinations are returned in reverse chronological order.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|------|----------|-------------|
| `trigger_id` | path | string | Yes | Trigger identifier |
| `limit` | query | integer | No | Maximum number of results (default: 20) |

**Example request:**

```bash
curl https://parametricdata.io:8502/v1/triggers/flight-delay-del/determinations?limit=5
```

**Example response:**

```json
{
  "trigger_id": "flight-delay-del",
  "determinations": [
    {
      "trigger_id": "flight-delay-del",
      "fired": true,
      "timestamp": "2026-03-25T10:00:00Z",
      "data_snapshot_hash": "sha256:abc123...",
      "signature": "ed25519:..."
    }
  ],
  "count": 1
}
```

---

### Get Status

```
GET /v1/status
```

Get data source health across all peril categories. Shows how many triggers have fresh data, stale data, or no data for each peril.

**Example request:**

```bash
curl https://parametricdata.io:8502/v1/status
```

**Example response:**

```json
{
  "perils": {
    "flight_delay": {
      "label": "Flight Delay",
      "total": 144,
      "cached": 130,
      "stale": 10,
      "no_data": 4,
      "coverage_pct": 90
    },
    "earthquake": {
      "label": "Earthquake",
      "total": 10,
      "cached": 10,
      "stale": 0,
      "no_data": 0,
      "coverage_pct": 100
    }
  },
  "total_triggers": 521
}
```

---

### List Perils

```
GET /v1/perils
```

List all peril categories with their display labels.

**Example request:**

```bash
curl https://parametricdata.io:8502/v1/perils
```

**Example response:**

```json
{
  "perils": {
    "flight_delay": "Flight Delay",
    "air_quality": "Air Quality",
    "wildfire": "Wildfire",
    "drought": "Drought",
    "extreme_weather": "Extreme Weather",
    "earthquake": "Earthquake",
    "marine": "Marine / Shipping",
    "flood": "Flood",
    "cyclone": "Tropical Cyclone",
    "crop": "Crop / NDVI",
    "solar": "Solar / Space Weather",
    "health": "Health / Pandemic"
  },
  "count": 12
}
```

---

### List Ports

```
GET /v1/ports
```

List all monitored marine ports with their coordinates and UN/LOCODE identifiers.

**Example request:**

```bash
curl https://parametricdata.io:8502/v1/ports
```

**Example response:**

```json
{
  "ports": [
    {
      "id": "port-sgp-jurong",
      "name": "Port of Singapore (Jurong)",
      "city": "Singapore",
      "country": "Singapore",
      "lat": 1.2647,
      "lon": 103.7518,
      "un_locode": "SGSIN",
      "tier": "tier1"
    }
  ],
  "count": 10
}
```

---

### Get Model History

```
GET /v1/triggers/{trigger_id}/model-history
```

Get machine learning model version history for a trigger (when available).

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|------|----------|-------------|
| `trigger_id` | path | string | Yes | Trigger identifier |
| `limit` | query | integer | No | Maximum number of results (default: 20) |

**Example request:**

```bash
curl https://parametricdata.io:8502/v1/triggers/flight-delay-del/model-history?limit=5
```

**Example response:**

```json
{
  "trigger_id": "flight-delay-del",
  "versions": [],
  "count": 0
}
```

## Error Responses

All errors return JSON with a `detail` field:

```json
{"detail": "error message"}
```

| Status Code | Description |
|-------------|-------------|
| 401 | Missing `X-API-Key` header (when auth is enabled) |
| 403 | Invalid API key |
| 404 | Trigger or resource not found |
| 500 | Internal server error |

## Rate Limits

No rate limits currently enforced. Subject to change. If you are building a high-traffic integration, please reach out.

## SDKs and Libraries

### Python

```python
import httpx

base = "https://parametricdata.io:8502/v1"

# List earthquake triggers
resp = httpx.get(f"{base}/triggers", params={"peril": "earthquake"})
triggers = resp.json()["triggers"]
for t in triggers:
    print(f"{t['id']}: {t['location_label']} — {'data available' if t['has_data'] else 'no data'}")
```

### JavaScript / Node.js

```javascript
const base = "https://parametricdata.io:8502/v1";

const resp = await fetch(`${base}/triggers?peril=earthquake`);
const { triggers, count } = await resp.json();
console.log(`${count} earthquake triggers`);
```

## Source Code

The API source is open: [`gad/api/main.py`](https://github.com/nittchan/GAD/blob/main/gad/api/main.py)

Response models: [`gad/api/models.py`](https://github.com/nittchan/GAD/blob/main/gad/api/models.py)
