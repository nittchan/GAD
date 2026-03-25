# Parametric Data

**The world's first open-source actuarial data platform for parametric insurance.**

[parametricdata.io](https://parametricdata.io)

Parametric Data monitors real-world risks — flight delays, air quality, wildfires, droughts, earthquakes, extreme weather, port congestion, floods, tropical cyclones, crop stress, solar storms, and disease outbreaks — and evaluates how well parametric insurance triggers perform against them. 521 triggers. 144 airports. 10 ports. 12 peril categories. 15 data sources. All open. All free.

## What you see

Open [parametricdata.io](https://parametricdata.io) and you get a live risk map of the world. Every dot is a parametric insurance trigger being monitored in real time. Click any dot to see its full profile — current value, threshold, status, and (when available) historical basis risk with Spearman correlation, Lloyd's alignment, and a downloadable PDF report.

## Why it matters

Parametric insurance pays when a trigger fires — a rainfall threshold, a flight delay, an earthquake magnitude. The actuarial math behind these triggers has always been proprietary. Parametric Data makes it open, auditable, and verifiable.

Every trigger determination can be cryptographically signed, hash-chained, and independently verified. A reinsurer can open a URL and see proof — no proprietary software required.

## Coverage

| Peril | Triggers | Data sources | Coverage |
|-------|----------|-------------|----------|
| Flight delay | 144 | AviationStack, OpenSky | 144 airports across 6 continents |
| Air quality | 125 | AirNow EPA, WAQI, OpenAQ | Global + authoritative US EPA data |
| Extreme weather | 144 | Open-Meteo | Heat, freeze, wind, rainfall at every airport |
| Earthquake | 10 | USGS | Major seismic zones worldwide |
| Wildfire | 8 | NASA FIRMS (VIIRS + MODIS) | California, Australia, Amazon, Siberia, Europe, Indonesia |
| Drought | 5 | CHIRPS, NASA GPM IMERG | Kenya, India, Ethiopia, Sahel, Brazil |
| Marine / Shipping | 20 | AISstream | 10 tier-1 ports: Singapore, Rotterdam, Shanghai, LA, JNPT, Jebel Ali, Hamburg, Colombo, Port Klang, Busan |
| Flood | 20 | USGS Water Services | 20 river gauge locations across US flood-prone zones |
| Cyclone | 20 | NOAA NHC | 20 high-exposure coastal locations, active storm proximity |
| Crop / NDVI | 10 | Copernicus/MODIS | Vegetation health index for key agricultural regions |
| Solar / Space Weather | 5 | NOAA SWPC | Geomagnetic storm and solar flare monitoring |
| Health / Pandemic | 10 | WHO DON | Disease outbreak alerts from WHO global surveillance |

## Run it yourself

```bash
git clone https://github.com/nittchan/GAD.git
cd GAD
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python -m gad.monitor.fetcher    # fetch live data (~60 seconds)
streamlit run dashboard/app.py   # open the dashboard
```

## Verify a determination

```bash
python -m gad.verify https://oracle.parametricdata.io/determination/{uuid}
python -m gad.verify --chain registry/   # verify the full hash chain
```

Or in Python:

```python
from gad.engine import verify_determination
from gad.engine.models import TriggerDetermination

det = TriggerDetermination(**determination_json)
print(verify_determination(det, public_key_bytes))  # True
```

## Architecture

```
parametricdata.io
├── Global Monitor        Live risk map (521 triggers, 12 perils)
├── Trigger Profile       Click any trigger → full basis risk analysis
├── Compare               Side-by-side trigger comparison
├── Build Your Own        4-step wizard → custom trigger
├── Expert Mode           JSON editor → full schema control
├── Monitor Status        Data source health dashboard
└── Oracle Ledger         Signed determinations + chain verification

Background fetcher (every 15 min)
├── AviationStack         Flight schedules (tier-1 airports)
├── OpenSky Network       Flight departures (all airports)
├── AirNow EPA            US air quality (authoritative)
├── WAQI                  Global air quality
├── NASA FIRMS            Wildfire (VIIRS + MODIS dual satellite)
├── Open-Meteo            Weather forecasts
├── CHIRPS                Monthly rainfall
├── NASA GPM IMERG        Daily precipitation
├── USGS Earthquake       Earthquake detection
├── AISstream             Marine vessel tracking (WebSocket)
├── USGS Water Services   Flood river gauge levels
├── NOAA NHC              Tropical cyclone tracking
├── Copernicus/MODIS      Crop / NDVI vegetation health
├── NOAA SWPC             Solar/space weather alerts
└── WHO DON               Health/pandemic outbreak alerts

Oracle layer (v0.2.2)
├── Ed25519 signing       Every determination cryptographically signed
├── Hash chain            Append-only JSONL log with chain verification
├── Key registry          Public keys at /.well-known/oracle-keys.json
└── Cloudflare Worker     /determination/{uuid} — permanent public ledger
```

## REST API

```
GET /v1/triggers                      — all triggers with status
GET /v1/triggers/{id}                 — single trigger profile
GET /v1/triggers/{id}/basis-risk      — precomputed Spearman report
GET /v1/triggers/{id}/determinations  — oracle log
GET /v1/triggers/{id}/model-history   — model version audit trail
GET /v1/triggers/{id}/model-drift     — drift detection status
GET /v1/intelligence/peril-patterns   — per-peril firing rates
GET /v1/intelligence/location/{lat}/{lon} — triggers near a point
GET /v1/status                        — per-peril health
GET /v1/ports                         — marine port list
GET /v1/perils                        — peril categories
GET /v1/docs                          — OpenAPI documentation
```

Open by default. API key auth opt-in via `API_REQUIRE_AUTH=true` + `X-API-Key` header. Full guide: [docs/API_GUIDE.md](docs/API_GUIDE.md).

## MCP Server (for AI agents)

```bash
python -m gad.mcp.server   # JSON-RPC 2.0 over stdin/stdout
```

Tools: `check_trigger_status`, `list_triggers_by_location`, `get_basis_risk`, `list_perils`.

Full API documentation: [docs/API_GUIDE.md](docs/API_GUIDE.md)

## Security

The public dashboard makes **zero external API calls**. All data is pre-fetched by a background worker and served from a local cache. 10,000 concurrent users cost the same in API calls as zero users.

## Contributing

Add a new airport: edit `gad/monitor/airports.py` — triggers auto-generate. If the airport is >15km from the city centre, set `city_lat`/`city_lon` so AQI queries hit the right location.
Add a new data source: create a file in `gad/monitor/sources/`.
Add a new peril: update `gad/monitor/triggers.py` and wire into the fetcher.

```bash
pytest   # run tests before submitting
```

## Author

**Nitthin Chandran Nair**

Built with [Claude Code](https://claude.ai/claude-code). Powered by [OrbitCover](https://orbitcover.com) (MedPiper Technologies — backed by Y Combinator).

## License

- **Engine:** AGPL-3.0 — see [LICENSE-engine](LICENSE-engine)
- **Schema:** MIT — see [LICENSE-schema](LICENSE-schema)
