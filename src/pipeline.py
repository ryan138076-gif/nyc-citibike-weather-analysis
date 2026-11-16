"""Reproducible Citi Bike + NOAA processing for SI 618 Milestones 1 and 2.

The pipeline streams every CSV member in each official monthly ZIP, performs
exact cross-chunk/cross-file ride-ID deduplication with SQLite, aggregates valid
trips to calendar days, and joins the result one-to-one to Central Park weather.

``--grain hourly`` (Milestone 2) runs the identical cleaning pass but also counts
valid rides by the local clock hour of ``started_at`` and places them on the
8,784-hour UTC grid of 2024. Citi Bike timestamps carry no UTC offset, so the
repeated 01:00 hour of 2024-11-03 cannot be split: both elapsed hours are left
missing (never zero) and their combined count is audited. The M1 daily outputs
are not rewritten in hourly mode.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
from pathlib import Path
import sqlite3
from urllib.request import urlretrieve
import zipfile

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_BIKE = ROOT / "data/raw/citibike"
RAW_WEATHER = ROOT / "data/raw/weather"
PROCESSED = ROOT / "data/processed"
WEATHER_URL = (
    "https://www.ncei.noaa.gov/access/services/data/v1?"
    "dataset=daily-summaries&stations=USW00094728&"
    "startDate=2024-01-01&endDate=2024-12-31&"
    "dataTypes=PRCP,TMAX,TMIN&units=metric&format=csv"
)
USECOLS = ["ride_id", "started_at", "ended_at", "member_casual"]
STUDY_START = pd.Timestamp("2024-01-01")
STUDY_END = pd.Timestamp("2024-12-31")
LOCAL_TZ = "America/New_York"
SPRING_GAP_HOUR = pd.Timestamp("2024-03-10 02:00")  # naive local hour that never occurred
FALL_REPEAT_HOUR = pd.Timestamp("2024-11-03 01:00")  # naive local hour that occurred twice


def download_weather() -> Path:
    """Download the public NOAA Central Park daily-summary extract if absent."""
    RAW_WEATHER.mkdir(parents=True, exist_ok=True)
    target = RAW_WEATHER / "noaa_2024.csv"
    if not target.exists():
        print(f"Downloading NOAA weather -> {target}", flush=True)
        urlretrieve(WEATHER_URL, target)
    return target


def download_month(month: int, year: int = 2024) -> Path:
    """Download one official Citi Bike archive, checking both used suffixes."""
    RAW_BIKE.mkdir(parents=True, exist_ok=True)
    prefix = f"{year}{month:02d}-citibike-tripdata"
    existing = sorted(RAW_BIKE.glob(prefix + "*.zip"))
    for candidate in existing:
        if zipfile.is_zipfile(candidate):
            return candidate
        candidate.unlink(missing_ok=True)

    for suffix in (".csv.zip", ".zip"):
        target = RAW_BIKE / f"{prefix}{suffix}"
        try:
            print(f"Downloading {target.name}", flush=True)
            urlretrieve(f"https://s3.amazonaws.com/tripdata/{target.name}", target)
            if zipfile.is_zipfile(target):
                return target
        except Exception:
            pass
        target.unlink(missing_ok=True)
    raise FileNotFoundError(
        f"Cannot download {prefix}; check the Citi Bike System Data archive."
    )


def _counter_frame(counter: Counter, value_name: str) -> pd.DataFrame:
    frame = pd.DataFrame({"date": sorted(counter)})
    frame["date"] = pd.to_datetime(frame["date"])
    frame[value_name] = frame["date"].dt.strftime("%Y-%m-%d").map(counter).astype(int)
    return frame


def aggregate_trips(
    paths: list[Path], chunksize: int = 200_000, hourly: bool = False
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    """Stream and clean all trip CSVs, returning daily data and live audits.

    A temporary SQLite table provides exact global ID uniqueness without holding
    tens of millions of IDs in RAM. Two genuine alternatives are calculated in
    the same pass: counting any parseable trip start without the duration/ID
    validity rule, and assigning valid trips to their end date instead.

    With ``hourly=True`` the same valid trips are also counted by the naive local
    hour of ``started_at``; the fifth return value then holds those counters and
    a DST audit. The eligibility rules are not changed.
    """
    counts: Counter = Counter()
    members: Counter = Counter()
    casuals: Counter = Counter()
    naive_start_counts: Counter = Counter()
    end_date_counts: Counter = Counter()
    hour_counts: Counter = Counter()
    hour_members: Counter = Counter()
    hour_casuals: Counter = Counter()
    dst_audit: Counter = Counter()
    audit_rows: list[dict] = []
    inventory_rows: list[dict] = []

    PROCESSED.mkdir(parents=True, exist_ok=True)
    sqlite_path = PROCESSED / ".ride_ids.sqlite"
    sqlite_path.unlink(missing_ok=True)
    connection = sqlite3.connect(sqlite_path)
    connection.execute("PRAGMA journal_mode=OFF")
    connection.execute("PRAGMA synchronous=OFF")
    connection.execute("PRAGMA temp_store=MEMORY")
    connection.execute("CREATE TABLE seen (ride_id TEXT PRIMARY KEY) WITHOUT ROWID")
    connection.execute(
        "CREATE TEMP TABLE incoming (ride_id TEXT PRIMARY KEY) WITHOUT ROWID"
    )

    try:
        for archive_value in paths:
            archive = Path(archive_value)
            if not zipfile.is_zipfile(archive):
                raise ValueError(f"Not a valid ZIP archive: {archive}")
            with zipfile.ZipFile(archive) as zipped:
                csv_members = sorted(
                    name
                    for name in zipped.namelist()
                    if name.lower().endswith(".csv")
                    and not name.startswith("__MACOSX/")
                )
                if not csv_members:
                    raise ValueError(f"No CSV members in {archive.name}")

                for member_name in csv_members:
                    with zipped.open(member_name) as source:
                        raw_columns = pd.read_csv(source, nrows=0).columns.tolist()
                    missing_columns = sorted(set(USECOLS) - set(raw_columns))
                    if missing_columns:
                        raise ValueError(
                            f"{archive.name}/{member_name} missing {missing_columns}"
                        )

                    file_raw_rows = 0
                    file_kept_rows = 0
                    file_chunks = 0
                    with zipped.open(member_name) as source:
                        reader = pd.read_csv(source, usecols=USECOLS, chunksize=chunksize)
                        for chunk_number, chunk in enumerate(reader, start=1):
                            file_chunks += 1
                            n_raw = len(chunk)
                            file_raw_rows += n_raw

                            missing_id = int(chunk["ride_id"].isna().sum())
                            invalid_member_type = int(
                                (~chunk["member_casual"].isin(["member", "casual"])).sum()
                            )
                            chunk["started_at"] = pd.to_datetime(
                                chunk["started_at"], errors="coerce", format="mixed"
                            )
                            chunk["ended_at"] = pd.to_datetime(
                                chunk["ended_at"], errors="coerce", format="mixed"
                            )
                            missing_start = int(chunk["started_at"].isna().sum())
                            missing_end = int(chunk["ended_at"].isna().sum())

                            naive = chunk.dropna(subset=["started_at"]).copy()
                            naive["date"] = naive["started_at"].dt.normalize()
                            naive = naive[naive["date"].between(STUDY_START, STUDY_END)]
                            naive_start_counts.update(
                                naive["date"].dt.strftime("%Y-%m-%d").value_counts().to_dict()
                            )

                            candidate = chunk.dropna(
                                subset=["ride_id", "started_at", "ended_at"]
                            ).copy()
                            nonpositive_mask = candidate["ended_at"] <= candidate["started_at"]
                            nonpositive_duration = int(nonpositive_mask.sum())
                            if hourly and nonpositive_duration:
                                bad = candidate[nonpositive_mask]
                                start_hour = bad["started_at"].dt.floor("h")
                                end_hour = bad["ended_at"].dt.floor("h")
                                dst_audit["nonpositive_duration_total"] += nonpositive_duration
                                dst_audit["nonpositive_on_2024_11_03"] += int(
                                    bad["started_at"].dt.normalize().eq(
                                        FALL_REPEAT_HOUR.normalize()
                                    ).sum()
                                )
                                dst_audit["nonpositive_within_repeated_0100_hour"] += int(
                                    (start_hour.eq(FALL_REPEAT_HOUR) & end_hour.eq(FALL_REPEAT_HOUR)).sum()
                                )
                                # A plausible clock-change ride: ends < 1 h "before" it starts.
                                dst_audit["nonpositive_explained_by_one_hour_shift"] += int(
                                    (
                                        start_hour.eq(FALL_REPEAT_HOUR)
                                        & (bad["ended_at"] + pd.Timedelta(hours=1) > bad["started_at"])
                                    ).sum()
                                )
                            candidate = candidate[
                                candidate["ended_at"] > candidate["started_at"]
                            ].copy()
                            candidate["date"] = candidate["started_at"].dt.normalize()
                            out_of_window = int(
                                (~candidate["date"].between(STUDY_START, STUDY_END)).sum()
                            )
                            candidate = candidate[
                                candidate["date"].between(STUDY_START, STUDY_END)
                            ].copy()
                            before_within = len(candidate)
                            candidate = candidate.drop_duplicates(
                                subset=["ride_id"], keep="first"
                            )
                            duplicate_within = before_within - len(candidate)

                            connection.execute("DELETE FROM incoming")
                            connection.executemany(
                                "INSERT OR IGNORE INTO incoming(ride_id) VALUES (?)",
                                ((str(value),) for value in candidate["ride_id"]),
                            )
                            duplicate_ids = {
                                row[0]
                                for row in connection.execute(
                                    "SELECT incoming.ride_id FROM incoming "
                                    "JOIN seen USING (ride_id)"
                                )
                            }
                            duplicate_global = len(duplicate_ids)
                            if duplicate_ids:
                                candidate = candidate[
                                    ~candidate["ride_id"].astype(str).isin(duplicate_ids)
                                ].copy()
                            connection.execute(
                                "INSERT OR IGNORE INTO seen(ride_id) SELECT ride_id FROM incoming"
                            )
                            connection.commit()

                            start_dates = candidate["date"].dt.strftime("%Y-%m-%d")
                            counts.update(start_dates.value_counts().to_dict())
                            members.update(
                                start_dates[
                                    candidate["member_casual"].eq("member")
                                ].value_counts().to_dict()
                            )
                            casuals.update(
                                start_dates[
                                    candidate["member_casual"].eq("casual")
                                ].value_counts().to_dict()
                            )
                            end_dates = candidate["ended_at"].dt.normalize()
                            end_dates = end_dates[
                                end_dates.between(STUDY_START, STUDY_END)
                            ].dt.strftime("%Y-%m-%d")
                            end_date_counts.update(end_dates.value_counts().to_dict())
                            if hourly:
                                start_hours = candidate["started_at"].dt.floor("h")
                                hour_counts.update(start_hours.value_counts().to_dict())
                                hour_members.update(
                                    start_hours[
                                        candidate["member_casual"].eq("member")
                                    ].value_counts().to_dict()
                                )
                                hour_casuals.update(
                                    start_hours[
                                        candidate["member_casual"].eq("casual")
                                    ].value_counts().to_dict()
                                )
                                cross_midnight = (
                                    candidate["ended_at"].dt.normalize()
                                    > candidate["date"]
                                )
                                dst_audit["valid_cross_midnight_rides"] += int(
                                    cross_midnight.sum()
                                )
                            file_kept_rows += len(candidate)

                            audit_rows.append(
                                {
                                    "archive": archive.name,
                                    "csv_member": member_name,
                                    "chunk": chunk_number,
                                    "raw_rows": n_raw,
                                    "missing_ride_id": missing_id,
                                    "missing_started_at": missing_start,
                                    "missing_ended_at": missing_end,
                                    "nonpositive_duration": nonpositive_duration,
                                    "invalid_member_type": invalid_member_type,
                                    "out_of_window": out_of_window,
                                    "duplicate_ids_within_chunk": duplicate_within,
                                    "duplicate_ids_global": duplicate_global,
                                    "kept_rows": len(candidate),
                                }
                            )
                    inventory_rows.append(
                        {
                            "archive": archive.name,
                            "csv_member": member_name,
                            "archive_bytes": archive.stat().st_size,
                            "source_columns": len(raw_columns),
                            "chunk_count": file_chunks,
                            "raw_rows": file_raw_rows,
                            "kept_rows": file_kept_rows,
                        }
                    )
                    print(
                        f"Processed {archive.name}/{member_name}: "
                        f"{file_raw_rows:,} raw, {file_kept_rows:,} kept",
                        flush=True,
                    )
    finally:
        connection.close()
        sqlite_path.unlink(missing_ok=True)

    if not counts:
        raise ValueError("No valid Citi Bike trip records were found")

    daily = _counter_frame(counts, "daily_rides")
    daily["member_rides"] = (
        daily["date"].dt.strftime("%Y-%m-%d").map(members).fillna(0).astype(int)
    )
    daily["casual_rides"] = (
        daily["date"].dt.strftime("%Y-%m-%d").map(casuals).fillna(0).astype(int)
    )

    alternatives = pd.DataFrame({"date": pd.date_range(STUDY_START, STUDY_END)})
    for label, values in (
        ("official_start_date_rides", counts),
        ("naive_start_date_rides", naive_start_counts),
        ("valid_end_date_rides", end_date_counts),
    ):
        alternatives[label] = (
            alternatives["date"]
            .dt.strftime("%Y-%m-%d")
            .map(values)
            .fillna(0)
            .astype(int)
        )
    hourly_parts = {
        "rides": hour_counts,
        "member": hour_members,
        "casual": hour_casuals,
        "dst_audit": dict(dst_audit),
    }
    return (
        daily,
        pd.DataFrame(audit_rows),
        pd.DataFrame(inventory_rows),
        alternatives,
        hourly_parts,
    )


def build_hourly(
    hourly_parts: dict, months: tuple[int, ...]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Place naive-local-hour counts on the elapsed-hour UTC grid of the study months.

    Returns the hourly bike table and a one-row DST/coverage audit. Hours inside
    the processed months with no valid ride start are true zeros; the two
    elapsed hours that share the naive label 2024-11-03 01:00 are NaN.
    """
    first = pd.Timestamp(f"2024-{min(months):02d}-01")
    last = pd.Timestamp(f"2024-{max(months):02d}-01") + pd.offsets.MonthBegin()
    utc = pd.date_range(
        first.tz_localize(LOCAL_TZ).tz_convert("UTC"),
        last.tz_localize(LOCAL_TZ).tz_convert("UTC"),
        freq="h",
        inclusive="left",
    )
    local = utc.tz_convert(LOCAL_TZ)
    naive_local = local.tz_localize(None)
    table = pd.DataFrame(
        {
            "hour_start_utc": utc,
            "hour_start_local": local,
            "date_local": naive_local.normalize(),
            "hour_of_day": naive_local.hour,
        }
    )
    # Only complete months are processed, so every hour of a processed month is in coverage.
    table = table[table["date_local"].dt.month.isin(months)].reset_index(drop=True)
    naive_key = table["hour_start_local"].dt.tz_localize(None)
    for column, counter in (
        ("hourly_rides", hourly_parts["rides"]),
        ("member_rides", hourly_parts["member"]),
        ("casual_rides", hourly_parts["casual"]),
    ):
        table[column] = naive_key.map(counter).fillna(0).astype("Int64")

    ambiguous = naive_key.eq(FALL_REPEAT_HOUR)
    table["dst_flag"] = "none"
    table.loc[ambiguous, "dst_flag"] = "fall_ambiguous"
    table.loc[ambiguous, ["hourly_rides", "member_rides", "casual_rides"]] = pd.NA

    grid_keys = set(naive_key)
    off_grid = {
        hour: n for hour, n in hourly_parts["rides"].items() if hour not in grid_keys
    }
    audit = {
        "grid_hours": len(table),
        "grid_unique_utc_keys": int(table["hour_start_utc"].nunique()),
        "fall_ambiguous_hours_set_missing": int(ambiguous.sum()),
        "fall_ambiguous_combined_rides": int(hourly_parts["rides"].get(FALL_REPEAT_HOUR, 0)),
        "spring_gap_ride_starts": int(hourly_parts["rides"].get(SPRING_GAP_HOUR, 0)),
        "rides_off_grid_total": int(sum(off_grid.values())),
        "zero_ride_hours": int(table["hourly_rides"].eq(0).sum()),
        **{k: int(v) for k, v in hourly_parts["dst_audit"].items()},
    }
    return table, pd.DataFrame([audit])


def reconcile_with_daily(
    hourly_table: pd.DataFrame, hourly_parts: dict, daily: pd.DataFrame
) -> pd.DataFrame:
    """Compare hourly counts summed by local date with the daily counts.

    Rides that are not on the grid (the fall-ambiguous hour, any spring-gap
    starts) are added back from the counters, so a correct build matches exactly.
    """
    by_date = (
        hourly_table.groupby("date_local")["hourly_rides"].sum(min_count=1).astype("Int64")
    )
    grid_keys = set(hourly_table["hour_start_local"].dt.tz_localize(None))
    added = Counter()
    for hour, n in hourly_parts["rides"].items():
        if hour not in grid_keys or hour == FALL_REPEAT_HOUR:
            added[hour.normalize()] += n
    result = daily[["date", "daily_rides"]].rename(columns={"date": "date_local"}).copy()
    result["hourly_sum"] = result["date_local"].map(by_date).fillna(0).astype(int)
    result["off_grid_or_ambiguous"] = result["date_local"].map(added).fillna(0).astype(int)
    result["difference"] = (
        result["hourly_sum"] + result["off_grid_or_ambiguous"] - result["daily_rides"]
    )
    return result


def load_weather(path: Path) -> tuple[pd.DataFrame, dict]:
    """Validate and standardize the NOAA daily-summary extract."""
    raw = pd.read_csv(path)
    needed = {"STATION", "DATE", "PRCP", "TMAX", "TMIN"}
    if not needed.issubset(raw.columns):
        raise ValueError(f"Weather fields missing: {sorted(needed - set(raw.columns))}")
    if set(raw["STATION"].dropna().astype(str).unique()) != {"USW00094728"}:
        raise ValueError("Weather extract contains a station other than USW00094728")

    weather = raw.rename(
        columns={"PRCP": "prcp_mm", "TMAX": "tmax_c", "TMIN": "tmin_c"}
    ).copy()
    weather["date"] = pd.to_datetime(weather["DATE"], errors="coerce").dt.normalize()
    for column in ["prcp_mm", "tmax_c", "tmin_c"]:
        weather[column] = pd.to_numeric(weather[column], errors="coerce")
    bad_dates = int(weather["date"].isna().sum())
    weather = weather.dropna(subset=["date"])
    duplicate_dates = int(weather["date"].duplicated().sum())
    if duplicate_dates:
        raise ValueError(
            f"NOAA contains {duplicate_dates} duplicate dates; investigate before merging"
        )
    weather["avg_temp_c"] = (weather["tmax_c"] + weather["tmin_c"]) / 2
    weather = weather[weather["date"].between(STUDY_START, STUDY_END)].copy()
    audit = {
        "weather_raw_rows": len(raw),
        "weather_raw_columns": raw.shape[1],
        "weather_invalid_dates": bad_dates,
        "weather_duplicate_dates": duplicate_dates,
        "weather_date_min": weather["date"].min().strftime("%Y-%m-%d"),
        "weather_date_max": weather["date"].max().strftime("%Y-%m-%d"),
        "weather_missing_prcp": int(weather["prcp_mm"].isna().sum()),
        "weather_missing_tmax": int(weather["tmax_c"].isna().sum()),
        "weather_missing_tmin": int(weather["tmin_c"].isna().sum()),
    }
    return weather[["date", "prcp_mm", "tmax_c", "tmin_c", "avg_temp_c"]], audit


def merge_daily(
    daily: pd.DataFrame,
    weather: pd.DataFrame,
    start: str = "2024-01-01",
    end: str = "2024-12-31",
) -> tuple[pd.DataFrame, dict]:
    """Join at one-row-per-calendar-day grain with explicit match flags."""
    calendar = pd.DataFrame({"date": pd.date_range(start, end, freq="D")})
    calendar = calendar.merge(daily, on="date", how="left", validate="one_to_one")
    joined = calendar.merge(
        weather, on="date", how="left", validate="one_to_one", indicator=True
    )
    joined["is_weekend"] = joined["date"].dt.dayofweek.ge(5)
    joined["month"] = joined["date"].dt.month
    audit = {
        "calendar_days": len(calendar),
        "bike_dates_present": int(calendar["daily_rides"].notna().sum()),
        "bike_dates_missing": int(calendar["daily_rides"].isna().sum()),
        "weather_dates_matched": int(joined["_merge"].eq("both").sum()),
        "weather_dates_unmatched": int(joined["_merge"].eq("left_only").sum()),
        "missing_precipitation": int(joined["prcp_mm"].isna().sum()),
        "missing_average_temperature": int(joined["avg_temp_c"].isna().sum()),
        "merged_duplicate_dates": int(joined["date"].duplicated().sum()),
    }
    return joined, audit


def _build_data_description(
    merged: pd.DataFrame,
    trip_audit: pd.DataFrame,
    inventory: pd.DataFrame,
    weather: pd.DataFrame,
) -> pd.DataFrame:
    """Create the computed rubric table for source and merged variables."""
    bike_rows = int(trip_audit["raw_rows"].sum())
    bike_columns = int(inventory["source_columns"].max())
    source_missing = {
        "ride_id": int(trip_audit["missing_ride_id"].sum()),
        "started_at": int(trip_audit["missing_started_at"].sum()),
        "ended_at": int(trip_audit["missing_ended_at"].sum()),
        "member_casual": int(trip_audit["invalid_member_type"].sum()),
    }
    rows: list[dict] = []
    for field, dtype, unit in (
        ("ride_id", "string", "identifier"),
        ("started_at", "datetime64[ns]", "NYC local timestamp"),
        ("ended_at", "datetime64[ns]", "NYC local timestamp"),
        ("member_casual", "category", "member/casual"),
    ):
        missing_n = source_missing[field]
        rows.append(
            {
                "dataset": "Citi Bike raw trips",
                "rows": bike_rows,
                "columns": bike_columns,
                "row_grain": "one recorded ride",
                "field": field,
                "dtype_after_cleaning": dtype,
                "unit": unit,
                "missing_n": missing_n,
                "missing_pct": 100 * missing_n / bike_rows,
            }
        )
    for field, unit in (
        ("date", "calendar date"),
        ("prcp_mm", "millimeters"),
        ("tmax_c", "degrees Celsius"),
        ("tmin_c", "degrees Celsius"),
        ("avg_temp_c", "degrees Celsius; (TMAX+TMIN)/2"),
    ):
        missing_n = int(weather[field].isna().sum())
        rows.append(
            {
                "dataset": "NOAA Central Park daily weather",
                "rows": len(weather),
                "columns": 5,
                "row_grain": "one station-date",
                "field": field,
                "dtype_after_cleaning": str(weather[field].dtype),
                "unit": unit,
                "missing_n": missing_n,
                "missing_pct": 100 * missing_n / len(weather),
            }
        )
    merged_units = {
        "date": "calendar date",
        "daily_rides": "rides started per day",
        "member_rides": "member rides started per day",
        "casual_rides": "casual rides started per day",
        "prcp_mm": "millimeters",
        "tmax_c": "degrees Celsius",
        "tmin_c": "degrees Celsius",
        "avg_temp_c": "degrees Celsius; (TMAX+TMIN)/2",
        "is_weekend": "Boolean; Saturday/Sunday",
        "month": "calendar month number",
    }
    for field, unit in merged_units.items():
        missing_n = int(merged[field].isna().sum())
        rows.append(
            {
                "dataset": "Merged daily analysis table",
                "rows": len(merged),
                "columns": merged.shape[1],
                "row_grain": "one calendar date",
                "field": field,
                "dtype_after_cleaning": str(merged[field].dtype),
                "unit": unit,
                "missing_n": missing_n,
                "missing_pct": 100 * missing_n / len(merged),
            }
        )
    return pd.DataFrame(rows)


def run_hourly(
    archives: list[Path], months: tuple[int, ...]
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """M2: hourly ride counts from the unchanged M1 cleaning pass."""
    m1_daily_path = PROCESSED / "daily_bike_2024.csv"
    m1_daily = (
        pd.read_csv(m1_daily_path, parse_dates=["date"]) if m1_daily_path.exists() else None
    )
    daily, trip_audit, _, _, hourly_parts = aggregate_trips(archives, hourly=True)
    hourly_table, dst_audit = build_hourly(hourly_parts, months)
    reconciliation = reconcile_with_daily(hourly_table, hourly_parts, daily)
    if m1_daily is not None:
        m1 = m1_daily.set_index("date")["daily_rides"]
        reconciliation["m1_daily_rides"] = reconciliation["date_local"].map(m1).astype("Int64")
        reconciliation["matches_m1"] = reconciliation["daily_rides"].eq(
            reconciliation["m1_daily_rides"]
        )
    audit = {
        "generated_on": date.today().isoformat(),
        "months": " ".join(map(str, months)),
        "bike_archives": len(archives),
        "bike_raw_rows": int(trip_audit["raw_rows"].sum()),
        "bike_kept_rows": int(trip_audit["kept_rows"].sum()),
        "hourly_rides_on_grid": int(hourly_table["hourly_rides"].sum()),
        "reconciliation_dates": len(reconciliation),
        "reconciliation_mismatched_dates": int(reconciliation["difference"].ne(0).sum()),
        "m1_mismatched_dates": (
            int((~reconciliation["matches_m1"]).sum()) if m1_daily is not None else -1
        ),
        **dst_audit.iloc[0].to_dict(),
    }
    out = hourly_table.copy()
    for column in ("hour_start_utc", "hour_start_local"):
        out[column] = out[column].map(lambda ts: ts.isoformat())
    out["date_local"] = out["date_local"].dt.strftime("%Y-%m-%d")
    out.to_csv(PROCESSED / "hourly_bike_2024.csv", index=False)
    reconciliation.to_csv(PROCESSED / "hourly_daily_reconciliation.csv", index=False)
    pd.Series(audit, name="value").rename_axis("metric").to_csv(
        PROCESSED / "hourly_dst_audit.csv"
    )
    return hourly_table, trip_audit, audit


def run(
    months: tuple[int, ...] | list[int] = tuple(range(1, 13)),
    download: bool = False,
    grain: str = "daily",
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Run the complete pipeline and persist analysis plus audit outputs."""
    PROCESSED.mkdir(parents=True, exist_ok=True)
    months = tuple(sorted(set(months)))
    archives: list[Path | None] = []
    for month in months:
        if download:
            archives.append(download_month(month))
        else:
            archives.append(
                next(
                    iter(sorted(RAW_BIKE.glob(f"2024{month:02d}-citibike-tripdata*.zip"))),
                    None,
                )
            )
    if any(path is None for path in archives):
        missing = [
            month for month, path in zip(months, archives, strict=True) if path is None
        ]
        raise FileNotFoundError(
            f"Missing Citi Bike ZIPs for months {missing}; rerun with --download"
        )
    if grain == "hourly":
        return run_hourly([path for path in archives if path is not None], months)
    weather_path = download_weather() if download else RAW_WEATHER / "noaa_2024.csv"
    if not weather_path.exists():
        raise FileNotFoundError("Missing NOAA weather CSV; rerun with --download")

    daily, trip_audit, inventory, alternatives, _ = aggregate_trips(
        [path for path in archives if path is not None]
    )
    weather, weather_audit = load_weather(weather_path)
    start = f"2024-{min(months):02d}-01"
    end = (
        pd.Timestamp(f"2024-{max(months):02d}-01") + pd.offsets.MonthEnd()
    ).strftime("%Y-%m-%d")
    merged, merge_audit = merge_daily(daily, weather, start, end)
    combined_audit = {
        "generated_on": date.today().isoformat(),
        "study_start": start,
        "study_end": end,
        "bike_archives": len(archives),
        "bike_csv_members": len(inventory),
        "bike_raw_rows": int(trip_audit["raw_rows"].sum()),
        "bike_kept_rows": int(trip_audit["kept_rows"].sum()),
        "duplicate_ids_within_chunk": int(
            trip_audit["duplicate_ids_within_chunk"].sum()
        ),
        "duplicate_ids_global": int(trip_audit["duplicate_ids_global"].sum()),
        **weather_audit,
        **merge_audit,
    }

    merged.to_csv(PROCESSED / "daily_bike_weather_2024.csv", index=False)
    daily.to_csv(PROCESSED / "daily_bike_2024.csv", index=False)
    weather.to_csv(PROCESSED / "daily_weather_2024.csv", index=False)
    trip_audit.to_csv(PROCESSED / "trip_cleaning_audit.csv", index=False)
    inventory.to_csv(PROCESSED / "source_inventory.csv", index=False)
    alternatives.to_csv(PROCESSED / "decision_alternatives.csv", index=False)
    pd.DataFrame([combined_audit]).to_csv(PROCESSED / "merge_audit.csv", index=False)
    _build_data_description(merged, trip_audit, inventory, weather).to_csv(
        PROCESSED / "data_description.csv", index=False
    )
    return merged, trip_audit, combined_audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--months", nargs="+", type=int, default=list(range(1, 13)))
    parser.add_argument("--download", action="store_true")
    parser.add_argument(
        "--grain",
        choices=["daily", "hourly"],
        default="daily",
        help="daily = M1 outputs; hourly = M2 hourly counts (M1 files untouched)",
    )
    args = parser.parse_args()
    merged, cleaning, audit = run(args.months, args.download, args.grain)
    print(f"{args.grain.capitalize()} table: {merged.shape}")
    print(f"Trip chunks audited: {len(cleaning):,}")
    print(pd.Series(audit).to_string())


if __name__ == "__main__":
    main()
