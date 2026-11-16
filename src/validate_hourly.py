"""Merge hourly bike counts with hourly weather and run the M2 acceptance gates.

Inputs (from ``pipeline.py --grain hourly`` and ``fetch_hourly_weather.py``):
``hourly_bike_2024.csv``, ``hourly_weather_2024.csv``, ``hourly_dst_audit.csv``
and ``hourly_daily_reconciliation.csv`` in ``data/processed``.

Outputs: ``hourly_bike_weather_2024.csv`` (the M2 analysis table) and
``hourly_validation.csv`` (one row per gate). Exits non-zero if a gate fails.

Weather source rule (development plan section 6.2): use the NOAA LCD station
series when it covers at least 95% of hours overall and in every quarter;
otherwise use Open-Meteo. Both series stay in the table for comparison.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data/processed"
LOCAL_TZ = "America/New_York"
WET_THRESHOLD_MM = 0.2
COVERAGE_RULE = 0.95


def load() -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.DataFrame]:
    bike = pd.read_csv(PROCESSED / "hourly_bike_2024.csv")
    bike["hour_start_utc"] = pd.to_datetime(bike["hour_start_utc"], utc=True)
    for column in ("hourly_rides", "member_rides", "casual_rides"):
        bike[column] = bike[column].astype("Int64")
    weather = pd.read_csv(PROCESSED / "hourly_weather_2024.csv")
    weather["hour_start_utc"] = pd.to_datetime(weather["hour_start_utc"], utc=True)
    dst = pd.read_csv(PROCESSED / "hourly_dst_audit.csv", index_col="metric")["value"]
    recon = pd.read_csv(PROCESSED / "hourly_daily_reconciliation.csv")
    return bike, weather, dst, recon


def choose_source(table: pd.DataFrame) -> tuple[str, pd.DataFrame]:
    coverage = (
        table.assign(has_lcd=table["lcd_precip_mm"].notna())
        .groupby("quarter")["has_lcd"]
        .mean()
    )
    overall = table["lcd_precip_mm"].notna().mean()
    use_lcd = overall >= COVERAGE_RULE and bool((coverage >= COVERAGE_RULE).all())
    report = coverage.rename("lcd_precip_coverage").reset_index()
    report.loc[len(report)] = ["all", overall]
    return ("noaa_lcd" if use_lcd else "open_meteo"), report


def build(bike: pd.DataFrame, weather: pd.DataFrame) -> tuple[pd.DataFrame, str, pd.DataFrame]:
    table = bike.merge(
        weather, on="hour_start_utc", how="left", validate="one_to_one", indicator=True
    )
    local = table["hour_start_utc"].dt.tz_convert(LOCAL_TZ)
    naive = local.dt.tz_localize(None)
    table["hour_start_local"] = local
    table["date_local"] = naive.dt.normalize()
    table["hour_of_day"] = naive.dt.hour
    table["month"] = naive.dt.month
    table["quarter"] = "Q" + naive.dt.quarter.astype(str)
    table["day_of_week"] = naive.dt.dayofweek
    table["is_weekend"] = table["day_of_week"].ge(5)

    source, coverage = choose_source(table)
    prefix = "lcd" if source == "noaa_lcd" else "om"
    table["precipitation_mm"] = table[f"{prefix}_precip_mm"]
    table["temperature_c"] = table[f"{prefix}_temp_c"]
    table["weather_source"] = source
    precip = table["precipitation_mm"]
    table["is_rainy"] = (precip >= WET_THRESHOLD_MM).astype("boolean").mask(precip.isna())
    table["is_rainy_any"] = (precip > 0).astype("boolean").mask(precip.isna())
    table["precip_trace"] = table["lcd_trace"].astype("boolean") if prefix == "lcd" else pd.NA
    table["rain_category"] = pd.cut(
        precip,
        bins=[-0.001, 0.0, 2.5, float("inf")],
        labels=["no rain", "light (<=2.5 mm/h)", "heavier (>2.5 mm/h)"],
    ).astype("string")
    return table, source, coverage


def gates(
    table: pd.DataFrame, dst: pd.Series, recon: pd.DataFrame, source: str
) -> pd.DataFrame:
    full_year = set(table["month"].unique()) == set(range(1, 13))
    per_day = table.groupby("date_local").size()
    checks: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: object) -> None:
        checks.append((name, bool(ok), str(detail)))

    check("unique UTC keys", table["hour_start_utc"].is_unique, table["hour_start_utc"].nunique())
    if full_year:
        check("8,784 elapsed hours", len(table) == 8784, len(table))
        check("spring DST day has 23 hours", per_day.get(pd.Timestamp("2024-03-10")) == 23,
              per_day.get(pd.Timestamp("2024-03-10")))
        check("fall DST day has 25 hours", per_day.get(pd.Timestamp("2024-11-03")) == 25,
              per_day.get(pd.Timestamp("2024-11-03")))
        check("fall-ambiguous hours are missing, not zero",
              int(table.loc[table["dst_flag"].eq("fall_ambiguous"), "hourly_rides"].isna().sum()) == 2,
              table.loc[table["dst_flag"].eq("fall_ambiguous"), "hourly_rides"].tolist())
    other_days = per_day.drop([pd.Timestamp("2024-03-10"), pd.Timestamp("2024-11-03")], errors="ignore")
    check("every other day has 24 hours", bool(other_days.eq(24).all()), other_days.value_counts().to_dict())
    check("bike counts only missing at DST-ambiguous hours",
          table["hourly_rides"].isna().sum() == table["dst_flag"].eq("fall_ambiguous").sum(),
          int(table["hourly_rides"].isna().sum()))
    check("every hour joined to the weather grid", table["_merge"].eq("both").all(),
          table["_merge"].value_counts().to_dict())
    check("hourly sums reconcile with the same-run daily counts",
          int(recon["difference"].ne(0).sum()) == 0, int(recon["difference"].ne(0).sum()))
    if "matches_m1" in recon:
        check("daily counts equal the committed M1 daily table",
              bool(recon["matches_m1"].all()), int((~recon["matches_m1"].astype(bool)).sum()))
    check("no rides off the grid except audited DST hours",
          float(dst.get("rides_off_grid_total", 0)) == float(dst.get("spring_gap_ride_starts", 0)),
          f"off-grid {dst.get('rides_off_grid_total')}, spring gap {dst.get('spring_gap_ride_starts')}")
    check("no negative precipitation", bool((table["precipitation_mm"].dropna() >= 0).all()),
          float(table["precipitation_mm"].min()))
    check("plausible temperatures (-30 to 45 C)",
          bool(table["temperature_c"].dropna().between(-30, 45).all()),
          (float(table["temperature_c"].min()), float(table["temperature_c"].max())))
    check("missing rain kept as NaN (not 0)",
          int(table["is_rainy"].isna().sum()) == int(table["precipitation_mm"].isna().sum()),
          int(table["precipitation_mm"].isna().sum()))
    check("member + casual <= total", bool(
        (table["member_rides"] + table["casual_rides"] <= table["hourly_rides"]).dropna().all()), "")
    check("weather source chosen by coverage rule", True, source)
    return pd.DataFrame(checks, columns=["gate", "passed", "detail"])


COLUMNS = [
    "hour_start_utc", "hour_start_local", "date_local", "hour_of_day", "month", "quarter",
    "day_of_week", "is_weekend", "hourly_rides", "member_rides", "casual_rides", "dst_flag",
    "temperature_c", "precipitation_mm", "is_rainy", "is_rainy_any", "precip_trace",
    "rain_category", "weather_source", "lcd_precip_mm", "lcd_temp_c", "om_precip_mm", "om_temp_c",
]


def run() -> tuple[pd.DataFrame, pd.DataFrame]:
    bike, weather, dst, recon = load()
    table, source, coverage = build(bike, weather)
    results = gates(table, dst, recon, source)
    out = table[COLUMNS].copy()
    for column in ("hour_start_utc", "hour_start_local"):
        out[column] = out[column].map(lambda ts: ts.isoformat())
    out["date_local"] = out["date_local"].dt.strftime("%Y-%m-%d")
    out.to_csv(PROCESSED / "hourly_bike_weather_2024.csv", index=False)
    results.to_csv(PROCESSED / "hourly_validation.csv", index=False)
    coverage.to_csv(PROCESSED / "weather_source_coverage.csv", index=False)
    return results, coverage


def main() -> None:
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args()
    results, coverage = run()
    print(coverage.to_string(index=False))
    print(results.to_string(index=False))
    if not results["passed"].all():
        sys.exit(1)


if __name__ == "__main__":
    main()
