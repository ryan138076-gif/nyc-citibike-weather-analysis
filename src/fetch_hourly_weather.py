"""Fetch and standardize 2024 hourly weather for SI 618 Milestone 2.

Two candidate sources are fetched and put on the same 8,784-hour UTC grid so the
notebook can compare them (development plan section 6.2):

* NOAA Local Climatological Data (LCD), Central Park station 725053-94728, the
  same station as the M1 daily data. Routine hourly reports (``FM-15``) arrive
  near :51 local standard time; precipitation is in inches since the previous
  routine report, ``T`` marks a trace and an ``s`` suffix marks a suspect value.
* Open-Meteo Historical Weather API (reanalysis), requested in GMT. Hourly
  ``precipitation`` is the sum over the *preceding* hour, so the value stamped
  ``hour_start + 1 h`` describes the hour ``[hour_start, hour_start + 1 h)``.

Every hour of the output describes the interval [hour_start_utc, +1 h), i.e.
the same interval in which the counted bike rides start. Missing stays NaN.
"""
from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_WEATHER = ROOT / "data/raw/weather"
PROCESSED = ROOT / "data/processed"

# 2024 in New York: 2024-01-01 00:00 EST = 05:00Z ... 2024-12-31 23:00 EST = 04:00Z.
GRID_START_UTC = pd.Timestamp("2024-01-01 05:00", tz="UTC")
GRID_END_UTC = pd.Timestamp("2025-01-01 04:00", tz="UTC")
LST = "Etc/GMT+5"  # fixed UTC-5 (POSIX sign convention), i.e. US Eastern Standard Time

LCD_STATION = "72505394728"
LCD_URL = "https://www.ncei.noaa.gov/access/services/data/v1?" + urlencode(
    {
        "dataset": "local-climatological-data",
        "stations": LCD_STATION,
        "startDate": "2024-01-01",
        "endDate": "2025-01-01",
        "dataTypes": "HourlyPrecipitation,HourlyDryBulbTemperature,REPORT_TYPE",
        "format": "csv",
    }
)
OPEN_METEO_PARAMS = {
    "latitude": 40.7789,  # Central Park (Belvedere Castle area)
    "longitude": -73.9692,
    "start_date": "2024-01-01",
    "end_date": "2025-01-01",
    "hourly": "temperature_2m,precipitation",
    "timezone": "GMT",
}
OPEN_METEO_URL = "https://archive-api.open-meteo.com/v1/archive?" + urlencode(
    OPEN_METEO_PARAMS
)
OPEN_METEO_PRECIP_DOC = (
    "precipitation: Total precipitation (rain, showers, snow) sum of the preceding hour"
)


def hour_grid() -> pd.DataFrame:
    """The 8,784 elapsed hours of the 2024 New York calendar year, keyed in UTC."""
    utc = pd.date_range(GRID_START_UTC, GRID_END_UTC, freq="h")
    if len(utc) != 8784:
        raise AssertionError(f"Expected 8,784 hours, built {len(utc)}")
    return pd.DataFrame({"hour_start_utc": utc})


def fetch(force: bool = False) -> tuple[Path, Path]:
    """Download both raw sources once and archive request metadata."""
    RAW_WEATHER.mkdir(parents=True, exist_ok=True)
    lcd_path = RAW_WEATHER / "noaa_lcd_2024.csv"
    om_path = RAW_WEATHER / "open_meteo_2024_hourly.json"
    if force or not lcd_path.exists():
        print(f"Downloading NOAA LCD -> {lcd_path}", flush=True)
        with urlopen(LCD_URL, timeout=300) as response:
            lcd_path.write_bytes(response.read())
    if force or not om_path.exists():
        print(f"Downloading Open-Meteo -> {om_path}", flush=True)
        with urlopen(OPEN_METEO_URL, timeout=300) as response:
            om_path.write_bytes(response.read())
    metadata = {
        "fetched_on": date.today().isoformat(),
        "noaa_lcd": {"url": LCD_URL, "station": LCD_STATION, "time_basis": "LST (UTC-5)"},
        "open_meteo": {
            "url": OPEN_METEO_URL,
            "params": OPEN_METEO_PARAMS,
            "precipitation_definition": OPEN_METEO_PRECIP_DOC,
            "model": "default best_match (not pinned)",
        },
    }
    (RAW_WEATHER / "hourly_weather_metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    return lcd_path, om_path


def parse_lcd_precip(values: pd.Series) -> pd.DataFrame:
    """Parse LCD HourlyPrecipitation strings into mm plus trace/suspect flags."""
    text = values.astype("string").str.strip()
    trace = text.str.upper().eq("T")
    suspect = text.str.endswith("s", na=False)
    numeric = pd.to_numeric(text.str.rstrip("s"), errors="coerce")
    mm = numeric * 25.4
    mm = mm.mask(trace, 0.0)  # trace: measurable amount is zero; flagged separately
    return pd.DataFrame({"precip_mm": mm, "trace": trace, "suspect": suspect})


def build_lcd(lcd_path: Path) -> tuple[pd.DataFrame, dict]:
    raw = pd.read_csv(lcd_path, dtype=str)
    raw["REPORT_TYPE"] = raw["REPORT_TYPE"].str.strip()
    routine = raw[raw["REPORT_TYPE"].eq("FM-15")].copy()
    local_standard = pd.to_datetime(routine["DATE"], errors="raise")
    routine["obs_utc"] = local_standard.dt.tz_localize(LST).dt.tz_convert("UTC")
    # A routine report near :51 closes the hour that began at :00 of the same hour.
    routine["hour_start_utc"] = routine["obs_utc"].dt.floor("h")
    parsed = parse_lcd_precip(routine["HourlyPrecipitation"])
    routine = pd.concat([routine, parsed.set_index(routine.index)], axis=1)
    temp_f = pd.to_numeric(
        routine["HourlyDryBulbTemperature"].str.rstrip("s"), errors="coerce"
    )
    routine["temp_c"] = (temp_f - 32) * 5 / 9

    duplicates = int(routine["hour_start_utc"].duplicated().sum())
    hourly = (
        routine.sort_values("obs_utc")
        .groupby("hour_start_utc", as_index=False)
        .last()[["hour_start_utc", "precip_mm", "trace", "suspect", "temp_c"]]
    )
    grid = hour_grid().merge(hourly, on="hour_start_utc", how="left", validate="one_to_one")
    grid = grid.rename(
        columns={
            "precip_mm": "lcd_precip_mm",
            "trace": "lcd_trace",
            "suspect": "lcd_suspect",
            "temp_c": "lcd_temp_c",
        }
    )
    audit = {
        "lcd_raw_rows": len(raw),
        "lcd_routine_reports": len(routine),
        "lcd_duplicate_routine_hours": duplicates,
        "lcd_hours_with_routine_report": int(grid["hour_start_utc"].isin(hourly["hour_start_utc"]).sum()),
        "lcd_hours_missing_precip": int(grid["lcd_precip_mm"].isna().sum()),
        "lcd_hours_missing_temp": int(grid["lcd_temp_c"].isna().sum()),
        "lcd_trace_hours": int(grid["lcd_trace"].fillna(False).sum()),
        "lcd_suspect_hours": int(grid["lcd_suspect"].fillna(False).sum()),
    }
    return grid, audit


def build_open_meteo(om_path: Path) -> tuple[pd.DataFrame, dict]:
    payload = json.loads(om_path.read_text(encoding="utf-8"))
    if payload.get("utc_offset_seconds") != 0:
        raise ValueError("Open-Meteo response is not in GMT")
    hourly = pd.DataFrame(payload["hourly"])
    hourly["stamp_utc"] = pd.to_datetime(hourly["time"]).dt.tz_localize("UTC")
    if hourly["stamp_utc"].duplicated().any():
        raise ValueError("Open-Meteo returned duplicate timestamps")
    stamped = hourly.set_index("stamp_utc")
    grid = hour_grid()
    # Preceding-hour sum: interval [h, h+1) is reported at stamp h+1.
    grid["om_precip_mm"] = stamped["precipitation"].reindex(
        grid["hour_start_utc"] + pd.Timedelta(hours=1)
    ).to_numpy()
    # Instantaneous temperature at the start of the hour.
    grid["om_temp_c"] = stamped["temperature_2m"].reindex(grid["hour_start_utc"]).to_numpy()
    audit = {
        "om_grid_latitude": payload.get("latitude"),
        "om_grid_longitude": payload.get("longitude"),
        "om_elevation_m": payload.get("elevation"),
        "om_hours_missing_precip": int(grid["om_precip_mm"].isna().sum()),
        "om_hours_missing_temp": int(grid["om_temp_c"].isna().sum()),
        "om_negative_precip": int((grid["om_precip_mm"] < 0).sum()),
    }
    return grid, audit


def compare(weather: pd.DataFrame, threshold: float = 0.2) -> dict:
    both = weather.dropna(subset=["lcd_precip_mm", "om_precip_mm"])
    lcd_wet = both["lcd_precip_mm"] >= threshold
    om_wet = both["om_precip_mm"] >= threshold
    temp = weather.dropna(subset=["lcd_temp_c", "om_temp_c"])
    return {
        "hours_both_precip": len(both),
        f"lcd_wet_share_ge_{threshold}": float(lcd_wet.mean()),
        f"om_wet_share_ge_{threshold}": float(om_wet.mean()),
        "lcd_wet_share_gt_0": float((both["lcd_precip_mm"] > 0).mean()),
        "om_wet_share_gt_0": float((both["om_precip_mm"] > 0).mean()),
        "wet_dry_disagreement_share": float((lcd_wet != om_wet).mean()),
        "wet_dry_disagreement_among_any_wet": float(
            (lcd_wet != om_wet)[lcd_wet | om_wet].mean()
        ),
        "precip_correlation": float(both["lcd_precip_mm"].corr(both["om_precip_mm"])),
        "temp_correlation": float(temp["lcd_temp_c"].corr(temp["om_temp_c"])),
        "temp_mean_diff_lcd_minus_om": float((temp["lcd_temp_c"] - temp["om_temp_c"]).mean()),
        "lcd_annual_precip_mm": float(weather["lcd_precip_mm"].sum()),
        "om_annual_precip_mm": float(weather["om_precip_mm"].sum()),
    }


def run(force: bool = False) -> tuple[pd.DataFrame, dict]:
    lcd_path, om_path = fetch(force)
    lcd, lcd_audit = build_lcd(lcd_path)
    om, om_audit = build_open_meteo(om_path)
    weather = lcd.merge(om, on="hour_start_utc", how="inner", validate="one_to_one")
    if len(weather) != 8784:
        raise AssertionError("Weather grid lost hours in the merge")
    audit = {**lcd_audit, **om_audit, **compare(weather)}
    PROCESSED.mkdir(parents=True, exist_ok=True)
    out = weather.copy()
    out["hour_start_utc"] = out["hour_start_utc"].dt.strftime("%Y-%m-%dT%H:%M:%S%z")
    out.to_csv(PROCESSED / "hourly_weather_2024.csv", index=False)
    pd.Series(audit, name="value").rename_axis("metric").to_csv(
        PROCESSED / "weather_source_comparison.csv"
    )
    return weather, audit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--force", action="store_true", help="re-download raw files")
    args = parser.parse_args()
    _, audit = run(args.force)
    print(pd.Series(audit).to_string())


if __name__ == "__main__":
    main()
