# TODOS

## Phase 2

### Legacy Engine Cleanup (Scheduled)
**What:** Delete `gad/_engine_legacy.py`, `gad/_models_legacy.py`, and `gad/_io_legacy.py` after one safety cycle.
**Why:** Legacy modules are a short-lived migration safety net; keeping them too long risks accidental new imports.
**When:** Next PR or next commit after 24h with no regressions.
**Verification before delete:** `pytest tests/ -v` and legacy import sweep remains clean.
**Depends on:** Option A engine canonicalization commit `a21e66f4c19ae37561cc44bd552d3edf450f55a2`.

### SQLite Registry Layer
**What:** Add SQLite registry to persist trigger definitions and basis risk reports.
**Why:** Global trigger registry is the 10x vision (CVE for insurance). Flat YAML files won't scale past ~50 triggers. Schema intentionally deferred until Phase 1 proves computation output shape.
**Pros:** Enables query/filter/compare at scale. API-ready for Phase 3.
**Cons:** Schema design work, migration tooling, persistence complexity.
**Context:** Use SQLAlchemy or raw sqlite3. Design schema to match actual BasisRiskReport output from Phase 1. Pydantic models are already API-ready.
**Depends on:** Phase 1 completion — need real output to design schema.

### Regional/Spatial Trigger Support
**What:** Support triggers that reference a bounding box or region, not just a single lat/lon point.
**Why:** Real parametric insurance covers areas. A drought trigger for "central Kenya" needs spatial averaging. Point-only is a Phase 1 simplification.
**Pros:** Matches real-world trigger designs. Required for credible Lloyd's alignment.
**Cons:** Adds xarray dependency, spatial averaging logic, larger data files.
**Context:** Add bounding box specification to trigger YAML. Use xarray for NetCDF/GRIB reading. Compute spatial average before Spearman correlation.
**Depends on:** Phase 1 completion. Data manifest format must support regional data references.

### Automated Open Data Pipeline
**What:** Automated ingestion of ERA5, CHIRPS, and NOAA data with scheduled fetching, caching, and format normalization.
**Why:** Phase 1 uses bundled CSV files. For the registry to stay current, automated ingestion is needed.
**Pros:** Keeps back-tests current. Enables analysis without manual data prep.
**Cons:** External API dependencies (CDS API, FTP, NCEI). Rate limits, storage growth, pipeline monitoring.
**Context:** ERA5 via Copernicus CDS API. CHIRPS via FTP/HTTP. NOAA via NCEI API. Each has different auth, format, and update frequency. Start with one source.
**Depends on:** Phase 1 data loading patterns. Registry schema.

### Back-test Zero Trigger Fires Handling
**What:** Add error handling and test for the case where a trigger never fires in the historical period.
**Why:** Critical gap — degenerate confusion matrix could produce misleading basis risk scores silently.
**Pros:** Prevents silent failure. Clear user feedback ("trigger never fired — consider adjusting threshold").
**Cons:** None — ~10 lines of code + test.
**Context:** Check trigger_fires count == 0 in back-test function. Return warning result instead of degenerate matrix.
**Depends on:** Nothing — can be included in Phase 1 if prioritized.

## Design

### Full Design System (DESIGN.md)
**Completed:** v0.1.0 (2026-03-19)
**What:** Run /design-consultation to create DESIGN.md with complete color palette, typography scale, spacing grid, motion system, and component library.

### PDF/Export for Basis Risk Reports
**Completed:** v0.1.0 (2026-03-19)
**What:** Export a trigger's full basis risk profile as a PDF report. Implemented in `gad/engine/pdf_export.py` using reportlab. Includes trigger definition, score card, back-test timeline, scatter plot, Lloyd's checklist, and methodology notes.
