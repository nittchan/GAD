"""
Open-data pipeline (Phase 2). CHIRPS live fetch and conversion to engine series format.
ERA5 (Copernicus CDS API) and NOAA/NCEI can be added with the same pattern.
"""

from __future__ import annotations

import gzip
import re
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    import pandas as pd
    from gad._models_legacy import TriggerDef

try:
    import requests
except ImportError:
    requests = None  # type: ignore

try:
    import rasterio
    from rasterio.transform import rowcol
except ImportError:
    rasterio = None  # type: ignore
    rowcol = None  # type: ignore

# CHIRPS v2.0: https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_monthly/tifs/
CHIRPS_BASE = "https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_monthly/tifs"
DEFAULT_CACHE_DIR = Path("data/cache/chirps")
CHIRPS_LAT_LIMIT = 50  # CHIRPS covers 50°S–50°N


def get_cache_dir(cache_dir: Optional[Path] = None) -> Path:
    """Return pipeline cache root; create if missing."""
    out = Path(cache_dir) if cache_dir else DEFAULT_CACHE_DIR
    out.mkdir(parents=True, exist_ok=True)
    return out


def fetch_chirps_monthly(
    year: int,
    month: int,
    cache_dir: Optional[Path] = None,
) -> Path:
    """
    Download CHIRPS 2.0 monthly global GeoTIFF for the given year/month into cache.
    Returns path to the cached file (e.g. .tif.gz).

    CHIRPS v2 production ends Dec 2026; migrate to v3 when needed.
    """
    cache = get_cache_dir(cache_dir)
    month_str = f"{month:02d}"
    filename = f"chirps-v2.0.{year}.{month_str}.tif.gz"
    out_path = cache / filename
    if out_path.exists():
        return out_path
    url = f"{CHIRPS_BASE}/{filename}"
    if requests is None:
        raise RuntimeError(
            "Install 'requests' to use the pipeline. Then retry or download manually from "
            "https://data.chc.ucsb.edu/products/CHIRPS-2.0/"
        )
    resp = requests.get(url, timeout=60, stream=True)
    resp.raise_for_status()
    with open(out_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
    return out_path


def _chirps_filename_to_period(path: Path) -> str:
    """Parse chirps-v2.0.YYYY.MM.tif.gz -> YYYY-MM."""
    m = re.search(r"chirps-v[\d.]+\.(\d{4})\.(\d{2})", path.name)
    if not m:
        raise ValueError(f"Cannot parse year/month from CHIRPS filename: {path.name}")
    return f"{m.group(1)}-{m.group(2)}"


def _open_raster_path(raster_path: Path):
    """Open raster path; decompress .gz to a temp file if needed (rasterio does not open .gz directly)."""
    path = Path(raster_path)
    if path.suffix == ".gz" or path.name.endswith(".tif.gz"):
        with gzip.open(path, "rb") as gz:
            with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tmp:
                tmp.write(gz.read())
                tmp_path = Path(tmp.name)
        try:
            return rasterio.open(tmp_path), tmp_path
        except Exception:
            tmp_path.unlink(missing_ok=True)
            raise
    return rasterio.open(path), None


def _read_point_from_geotiff(raster_path: Path, lat: float, lon: float) -> float:
    """Read precipitation value at (lat, lon) from a CHIRPS GeoTIFF. Returns mm."""
    if rasterio is None:
        raise RuntimeError("rasterio is required for CHIRPS extraction. pip install rasterio")
    src, tmp_path = _open_raster_path(raster_path)
    with src:
        transform = src.transform
        row, col = rowcol(transform, lon, lat)
        if row < 0 or row >= src.height or col < 0 or col >= src.width:
            raise ValueError(
                f"Point ({lat}, {lon}) is outside raster extent (height={src.height}, width={src.width})"
            )
        window = rasterio.windows.Window(col, row, 1, 1)
        data = src.read(1, window=window)
        val = float(data[0, 0])
    if tmp_path is not None:
        tmp_path.unlink(missing_ok=True)
    return val


def raster_paths_to_series(
    raster_paths: list[Path],
    lat: float,
    lon: float,
    output_csv: Optional[Path] = None,
) -> "pd.DataFrame":
    """
    Extract point (lat, lon) time series from CHIRPS monthly GeoTIFFs.
    Returns DataFrame with columns: period, index_value, spatial_ref, loss_event, loss_proxy.
    spatial_ref = index_value (no regional mean); loss_event and loss_proxy = 0.
    If output_csv is set, writes CSV and returns the same DataFrame.
    """
    import pandas as pd

    if not raster_paths:
        raise ValueError("raster_paths must not be empty")
    if not (-CHIRPS_LAT_LIMIT <= lat <= CHIRPS_LAT_LIMIT):
        raise ValueError(
            f"CHIRPS covers 50°S–50°N; lat={lat} is outside range [-{CHIRPS_LAT_LIMIT}, {CHIRPS_LAT_LIMIT}]"
        )

    rows: list[dict] = []
    for path in sorted(raster_paths):
        if not path.is_file():
            raise FileNotFoundError(f"Raster not found: {path}")
        period = _chirps_filename_to_period(path)
        try:
            value = _read_point_from_geotiff(path, lat, lon)
        except Exception as e:
            raise RuntimeError(f"Failed to read {path.name}: {e}") from e
        rows.append({
            "period": period,
            "index_value": value,
            "spatial_ref": value,
            "loss_event": 0,
            "loss_proxy": 0.0,
        })
    df = pd.DataFrame(rows)
    if output_csv is not None:
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_csv, index=False)
    return df


def normalize_chirps_to_series(
    raster_path: Path,
    lat: float,
    lon: float,
    output_csv: Optional[Path] = None,
) -> Optional["pd.DataFrame"]:
    """
    Extract point (lat, lon) from a single CHIRPS raster. Convenience wrapper;
    for multiple months use raster_paths_to_series([paths], lat, lon, output_csv).
    """
    return raster_paths_to_series([raster_path], lat, lon, output_csv)


def run_chirps_fetch(
    start_year: int,
    start_month: int,
    end_year: int,
    end_month: int,
    cache_dir: Optional[Path] = None,
) -> list[Path]:
    """
    Fetch CHIRPS monthly rasters for the given range and return list of cached paths.
    """
    paths: list[Path] = []
    y, m = start_year, start_month
    while y < end_year or (y == end_year and m <= end_month):
        paths.append(fetch_chirps_monthly(y, m, cache_dir=cache_dir))
        m += 1
        if m > 12:
            m = 1
            y += 1
    return paths


def build_chirps_series_for_trigger(
    trigger: "TriggerDef",
    cache_dir: Optional[Path] = None,
    data_root: Optional[Path] = None,
) -> Path:
    """
    Fetch CHIRPS for the trigger's location and date range, convert to engine series CSV,
    write to cache, and return the CSV path. Use with make_live_manifest() and compute_basis_risk().

    Raises ValueError if lat/lon outside CHIRPS extent (50°S–50°N) or on fetch/conversion errors.
    """
    from gad._models_legacy import TriggerDef

    cache = get_cache_dir(cache_dir)
    series_dir = cache / "series"
    series_dir.mkdir(parents=True, exist_ok=True)
    out_csv = series_dir / f"{trigger.id}.csv"

    lat, lon = trigger.location.lat, trigger.location.lon
    start, end = trigger.date_range.start, trigger.date_range.end
    raster_paths = run_chirps_fetch(
        start.year, start.month, end.year, end.month, cache_dir=cache
    )
    raster_paths_to_series(raster_paths, lat, lon, output_csv=out_csv)
    return out_csv


def make_live_manifest(trigger_id: str, series_csv_path: Path, data_root: Path) -> "DataManifest":
    """
    Build a one-off DataManifest that maps trigger_id to the generated series CSV.
    data_root must be the root under which series_csv_path lives (e.g. project data dir).
    """
    from gad._models_legacy import DataManifest, SeriesRef

    try:
        rel = series_csv_path.resolve().relative_to(Path(data_root).resolve())
    except ValueError:
        raise ValueError(
            f"series_csv_path {series_csv_path} must be under data_root {data_root}"
        ) from None
    ref = SeriesRef(primary_series_csv=str(rel))
    return DataManifest(triggers={trigger_id: ref})
