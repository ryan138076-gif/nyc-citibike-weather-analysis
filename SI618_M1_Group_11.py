# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "marimo>=0.25,<0.26",
#     "matplotlib>=3.8,<4",
#     "numpy>=2,<3",
#     "pandas>=2.2,<3",
# ]
# ///

import marimo

__generated_with = "0.25.1"
app = marimo.App(width="medium")


@app.cell
def _():
    import base64
    import io
    import json
    from pathlib import Path
    import zlib

    import marimo as mo
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd
    return Path, base64, io, json, mo, np, pd, plt, zlib


@app.cell
def _(mo):
    mo.md(
        r"""
        # Title and group

        **Working title:** Weather and Daily NYC Citi Bike Ridership in 2024  
        **Group name:** Group 11  
        **Group members:**  
        - Yanran Chen — **uniqname:** yanranc  
        - Hanyang Liu — **uniqname:** hanyliu
        """
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## Overview

        This project studies how daily precipitation and temperature are associated
        with NYC Citi Bike demand during 2024, including whether the rain–ridership
        pattern looks different on weekdays and weekends. Citi Bike trip histories
        contain ride timestamps and rider type but no weather; NOAA provides daily
        precipitation and temperature but no measure of bike demand. Aggregating valid
        ride starts to dates and merging them with Central Park daily observations
        creates one tidy daily table in which weather and ridership can be compared.
        The merge therefore enables questions that neither source can answer alone.
        """
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## Research questions

        1. **How is daily precipitation associated with Citi Bike ridership?**  
           **Columns:** `prcp_mm`, `daily_rides`. Compare the distribution of daily
           rides for no rain (0 mm), light rain (more than 0 through 5 mm), and heavier
           rain (more than 5 mm). If there were no visible association, the three
           distributions would substantially overlap without an ordered change.

        2. **Is the relationship between temperature and daily ridership nonlinear?**  
           **Columns:** `avg_temp_c`, `daily_rides`. Examine the daily scatter and the
           descriptive median within 5 °C bands for a bend or peak. If there were no
           nonlinear pattern, the band medians would be approximately straight/monotonic
           or would show no clear direction.

        3. **Does the precipitation–ridership relationship differ between weekdays and
           weekends?**  
           **Columns:** `prcp_mm`, `daily_rides`, `is_weekend`. Compare rainy and dry
           daily-ride distributions separately for weekdays and weekends. If there were
           no visible difference, the rainy-versus-dry contrast would be similar in both
           groups.

        All three questions depend on columns brought together from both source datasets.
        """
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## Data sources

        - **Citi Bike Trip Histories** — published by NYC Bike Share / Citi Bike;
          [system data page](https://citibikenyc.com/system-data). Twelve official NYC
          monthly ZIPs for January–December 2024 were downloaded on **2026-10-14**.
          The [NYCBS Data Sharing Policy](https://citibikenyc.com/data-sharing-policy)
          grants a limited, royalty-free license for lawful analysis and permits the
          data as source material in non-commercial analyses, but prohibits publishing
          the data as a stand-alone dataset. Jersey City (`JC-`) archives were excluded.

        - **NOAA NCEI Daily Summaries** — published by NOAA/NCEI;
          [Daily Summaries API](https://www.ncei.noaa.gov/access/services/data/v1).
          Central Park station `USW00094728`, fields `PRCP`, `TMAX`, and `TMIN`, metric
          units, January 1–December 31, 2024; downloaded on **2026-10-14**. The
          [NOAA data-license statement](https://data.noaa.gov/docucomp/xmlComponent/show/690447)
          identifies NOAA-produced data as public-domain/CC0 materials; NOAA is credited
          as the source.

        **Match:** Citi Bike `started_at` is interpreted in the operating system's local
        New York calendar and normalized to `date`; NOAA `DATE` is normalized to the same
        `date`. The merge is validated as one-to-one after trip-level data are aggregated.
        A single Central Park station is a citywide weather proxy, not the exact condition
        at every trip origin.
        """
    )
    return


@app.cell(hide_code=True)
def _(Path, base64, io, json, pd, zlib):
    # Verified reduced outputs are embedded to keep this notebook portable.
    # When local processed files are unavailable, these data allow the analysis
    # to run without loading the 8+ GB collection of raw monthly ZIP files.
    # The same frames can be rebuilt from raw data with:
    # .venv/bin/python src/pipeline.py --months 1 2 ... 12
    EMBEDDED_DATA_B64 = """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"""

    project_root = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
    processed_dir = project_root / "data" / "processed"
    required_files = [
        "daily_bike_weather_2024.csv",
        "data_description.csv",
        "decision_alternatives.csv",
        "merge_audit.csv",
        "source_inventory.csv",
        "trip_cleaning_audit.csv",
    ]
    if all((processed_dir / name).exists() for name in required_files):
        data_origin = "verified local processed files"

        def load_csv(name, **kwargs):
            return pd.read_csv(processed_dir / name, **kwargs)
    else:
        embedded_files = json.loads(zlib.decompress(base64.b64decode(EMBEDDED_DATA_B64)))
        data_origin = "embedded verified reduced outputs"

        def load_csv(name, **kwargs):
            return pd.read_csv(io.StringIO(embedded_files[name]), **kwargs)

    merged = load_csv("daily_bike_weather_2024.csv", parse_dates=["date"])
    data_description = load_csv("data_description.csv")
    alternatives = load_csv("decision_alternatives.csv", parse_dates=["date"])
    merge_audit = load_csv("merge_audit.csv").iloc[0]
    source_inventory = load_csv("source_inventory.csv")
    cleaning_audit = load_csv("trip_cleaning_audit.csv")
    return (
        alternatives,
        cleaning_audit,
        data_description,
        data_origin,
        merge_audit,
        merged,
        source_inventory,
    )


@app.cell
def _(data_description, data_origin, merge_audit, mo):
    dataset_summary = (
        data_description[["dataset", "rows", "columns", "row_grain"]]
        .drop_duplicates()
        .reset_index(drop=True)
    )
    variable_table = data_description.copy()
    variable_table["missing_pct"] = variable_table["missing_pct"].round(3)
    mo.vstack(
        [
            mo.md("## Data description"),
            mo.md(
                f"Data loaded from **{data_origin}**. Counts, types, units, and "
                "missingness below are generated from the pipeline outputs, not typed "
                "from a template."
            ),
            mo.md("### Dataset size and row grain"),
            mo.ui.table(dataset_summary, pagination=False),
            mo.md("### Variables used by the research questions"),
            mo.ui.table(variable_table, pagination=True, page_size=20),
            mo.md(
                f"The merged table contains **{int(merge_audit['calendar_days']):,} "
                f"unique dates**. Citi Bike is trip-level before aggregation; NOAA is "
                "station-date-level; the merged table is calendar-date-level."
            ),
        ]
    )
    return dataset_summary, variable_table


@app.cell
def _(cleaning_audit, merge_audit, mo, source_inventory):
    monthly_audit = (
        cleaning_audit.groupby("archive", as_index=False)[
            [
                "raw_rows",
                "missing_ride_id",
                "missing_started_at",
                "missing_ended_at",
                "nonpositive_duration",
                "invalid_member_type",
                "out_of_window",
                "duplicate_ids_within_chunk",
                "duplicate_ids_global",
                "kept_rows",
            ]
        ]
        .sum()
    )
    total_removed = int(monthly_audit["raw_rows"].sum() - monthly_audit["kept_rows"].sum())
    mo.vstack(
        [
            mo.md("## Data manipulation"),
            mo.md(
                f"The pipeline opened **all {int(merge_audit['bike_csv_members'])} CSV "
                f"members** in **{int(merge_audit['bike_archives'])} monthly ZIPs** and "
                f"streamed them in 200,000-row chunks. It read "
                f"**{int(merge_audit['bike_raw_rows']):,}** trip rows and retained "
                f"**{int(merge_audit['bike_kept_rows']):,}** after requiring a ride ID, "
                "parseable start/end timestamps, positive duration, a 2024 start date, "
                "and exact global ride-ID uniqueness."
            ),
            mo.md(
                f"Exactly **{total_removed:,}** rows were excluded: "
                f"**{int(monthly_audit['nonpositive_duration'].sum()):,}** had a "
                "nonpositive duration and **"
                f"{int(monthly_audit['out_of_window'].sum()):,}** started outside the "
                "2024 study window. Missing required fields and duplicate ride IDs were "
                "both zero."
            ),
            mo.md("### Row-survival audit by monthly archive"),
            mo.ui.table(monthly_audit, pagination=True, page_size=12),
            mo.md("### ZIP / CSV inventory (every member was processed)"),
            mo.ui.table(source_inventory, pagination=True, page_size=10),
            mo.md(
                f"After trip starts were counted by date, a 366-day calendar was "
                f"one-to-one merged to NOAA on `date`: **"
                f"{int(merge_audit['weather_dates_matched']):,} matched, "
                f"{int(merge_audit['weather_dates_unmatched']):,} unmatched**. Missing "
                "ride days were not filled with zero; there were none in this full-year "
                "extract. `avg_temp_c` is the descriptive proxy `(tmax_c+tmin_c)/2`, "
                "`is_weekend` marks Saturday/Sunday, and `month` is 1–12."
            ),
        ]
    )
    return monthly_audit, total_removed


@app.cell
def _(merged, np, pd):
    analysis_days = merged.dropna(subset=["daily_rides", "prcp_mm", "avg_temp_c"]).copy()
    rain_order = ["No rain", "Light rain (0–5 mm)", "Heavier rain (>5 mm)"]
    analysis_days["rain_bin"] = pd.cut(
        analysis_days["prcp_mm"],
        bins=[-0.001, 0, 5, np.inf],
        labels=rain_order,
    )
    analysis_days["day_type"] = np.where(
        analysis_days["is_weekend"], "Weekend", "Weekday"
    )
    analysis_days["rain_status"] = np.where(
        analysis_days["prcp_mm"] > 0, "Rain", "No rain"
    )
    analysis_days["temp_bin"] = pd.cut(
        analysis_days["avg_temp_c"], bins=np.arange(-10, 36, 5), right=False
    )
    rain_summary = (
        analysis_days.groupby("rain_bin", observed=False)["daily_rides"]
        .agg(days="count", median_rides="median", mean_rides="mean")
        .reset_index()
    )
    temp_summary = (
        analysis_days.groupby("temp_bin", observed=True)["daily_rides"]
        .agg(days="count", median_rides="median", mean_rides="mean")
        .reset_index()
    )
    day_rain_summary = (
        analysis_days.groupby(["day_type", "rain_status"])["daily_rides"]
        .agg(days="count", median_rides="median", mean_rides="mean")
        .reset_index()
    )
    return analysis_days, day_rain_summary, rain_order, rain_summary, temp_summary


@app.cell
def _(mo):
    mo.md(
        "## Data visualisation\n\n"
        "All three figures use the 366 matched dates. No observation was removed for "
        "missing ridership, precipitation, or temperature. The plots describe "
        "associations only; season, holidays, system changes, and other factors may "
        "also shape daily demand."
    )
    return


@app.cell
def _(analysis_days, mo, plt, rain_order):
    _groups = [
        analysis_days.loc[analysis_days["rain_bin"].eq(label), "daily_rides"].values
        for label in rain_order
    ]
    fig1, _ax1 = plt.subplots(figsize=(9, 4.8))
    _boxes = _ax1.boxplot(_groups, patch_artist=True, widths=0.55, showfliers=True)
    for _patch, _color in zip(
        _boxes["boxes"], ["#2F6690", "#D9A441", "#C96C3B"], strict=True
    ):
        _patch.set_facecolor(_color)
        _patch.set_alpha(0.78)
    _ax1.set_xticks([1, 2, 3], rain_order)
    _ax1.set_title("Daily Citi Bike rides decline across precipitation categories (2024)")
    _ax1.set_xlabel("Daily precipitation category")
    _ax1.set_ylabel("Daily rides (count)")
    _ax1.grid(axis="y", alpha=0.22)
    fig1.tight_layout()
    mo.as_html(fig1)
    return fig1


@app.cell
def _(mo, rain_summary):
    _no_rain = rain_summary.loc[rain_summary["rain_bin"].eq("No rain")].iloc[0]
    _light = rain_summary.loc[
        rain_summary["rain_bin"].eq("Light rain (0–5 mm)")
    ].iloc[0]
    _heavy = rain_summary.loc[
        rain_summary["rain_bin"].eq("Heavier rain (>5 mm)")
    ].iloc[0]
    mo.vstack(
        [
            mo.ui.table(rain_summary.round({"median_rides": 0, "mean_rides": 0})),
            mo.md(
                f"**RQ1 observation.** Median ridership was **{_no_rain.median_rides:,.0f}** "
                f"across {_no_rain.days:.0f} no-rain days, **{_light.median_rides:,.0f}** "
                f"across {_light.days:.0f} light-rain days, and "
                f"**{_heavy.median_rides:,.0f}** across {_heavy.days:.0f} heavier-rain "
                "days. The ordered drop is descriptively consistent with lower demand "
                "on wetter days, but it is not a causal estimate."
            ),
        ]
    )
    return


@app.cell
def _(analysis_days, mo, plt, temp_summary):
    fig2, _ax2 = plt.subplots(figsize=(9, 4.8))
    _ax2.scatter(
        analysis_days["avg_temp_c"],
        analysis_days["daily_rides"],
        s=24,
        alpha=0.38,
        color="#2F6690",
        edgecolors="none",
        label="Daily observation",
    )
    _midpoints = temp_summary["temp_bin"].map(lambda interval: interval.mid).astype(float)
    _ax2.plot(
        _midpoints,
        temp_summary["median_rides"],
        color="#C96C3B",
        linewidth=2.2,
        marker="o",
        label="Median within 5 °C band",
    )
    _ax2.set_title("Ridership rises with temperature, then levels off (2024)")
    _ax2.set_xlabel("Daily mean-temperature proxy, (TMAX + TMIN) / 2 (°C)")
    _ax2.set_ylabel("Daily rides (count)")
    _ax2.grid(alpha=0.22)
    _ax2.legend(frameon=False)
    fig2.tight_layout()
    mo.as_html(fig2)
    return fig2


@app.cell
def _(mo, temp_summary):
    _peak_row = temp_summary.loc[temp_summary["median_rides"].idxmax()]
    _cold_row = temp_summary.iloc[0]
    _hot_row = temp_summary.iloc[-1]
    _display_temp = temp_summary.copy()
    _display_temp["temp_bin"] = _display_temp["temp_bin"].astype(str)
    mo.vstack(
        [
            mo.ui.table(_display_temp.round({"median_rides": 0, "mean_rides": 0})),
            mo.md(
                f"**RQ2 observation.** The 5 °C-band median climbed from "
                f"**{_cold_row.median_rides:,.0f} rides** in {_cold_row.temp_bin} °C to "
                f"a peak of **{_peak_row.median_rides:,.0f}** in {_peak_row.temp_bin} °C, "
                f"then was **{_hot_row.median_rides:,.0f}** in {_hot_row.temp_bin} °C. "
                "This bend is consistent with a nonlinear descriptive pattern, although "
                "the warmest band contains few days and temperature also tracks season."
            ),
        ]
    )
    return


@app.cell
def _(analysis_days, mo, plt):
    _labels = [
        "Weekday\nNo rain",
        "Weekday\nRain",
        "Weekend\nNo rain",
        "Weekend\nRain",
    ]
    _selectors = [
        ("Weekday", "No rain"),
        ("Weekday", "Rain"),
        ("Weekend", "No rain"),
        ("Weekend", "Rain"),
    ]
    _groups = [
        analysis_days.loc[
            analysis_days["day_type"].eq(day_type)
            & analysis_days["rain_status"].eq(rain_status),
            "daily_rides",
        ].values
        for day_type, rain_status in _selectors
    ]
    fig3, _ax3 = plt.subplots(figsize=(9, 4.8))
    _boxes3 = _ax3.boxplot(_groups, patch_artist=True, widths=0.55)
    for _patch, _color, _hatch in zip(
        _boxes3["boxes"],
        ["#2F6690", "#2F6690", "#D9A441", "#D9A441"],
        ["", "///", "", "///"],
        strict=True,
    ):
        _patch.set_facecolor(_color)
        _patch.set_alpha(0.78)
        _patch.set_hatch(_hatch)
    _ax3.set_xticks(range(1, 5), _labels)
    _ax3.set_title("Rainy days have lower ridership on weekdays and weekends (2024)")
    _ax3.set_xlabel("Day type and precipitation status (hatched = rain > 0 mm)")
    _ax3.set_ylabel("Daily rides (count)")
    _ax3.grid(axis="y", alpha=0.22)
    fig3.tight_layout()
    mo.as_html(fig3)
    return fig3


@app.cell
def _(day_rain_summary, mo):
    _pivot = day_rain_summary.pivot(
        index="day_type", columns="rain_status", values="median_rides"
    )
    _weekday_change = 100 * (
        _pivot.loc["Weekday", "Rain"] / _pivot.loc["Weekday", "No rain"] - 1
    )
    _weekend_change = 100 * (
        _pivot.loc["Weekend", "Rain"] / _pivot.loc["Weekend", "No rain"] - 1
    )
    mo.vstack(
        [
            mo.ui.table(
                day_rain_summary.round({"median_rides": 0, "mean_rides": 0})
            ),
            mo.md(
                f"**RQ3 observation.** Relative to dry days, median ridership was "
                f"**{abs(_weekday_change):.1f}% lower on rainy weekdays** and "
                f"**{abs(_weekend_change):.1f}% lower on rainy weekends**. Both groups "
                "show a lower rainy-day distribution; the weekday median contrast is "
                "about 5.6 percentage points larger. These unadjusted comparisons do not "
                "separate rain from season, holidays, or other daily factors."
            ),
        ]
    )
    return


@app.cell
def _(alternatives, cleaning_audit, merge_audit):
    official_total = int(alternatives["official_start_date_rides"].sum())
    naive_total = int(alternatives["naive_start_date_rides"].sum())
    invalid_added = naive_total - official_total
    invalid_day = alternatives.loc[
        alternatives["naive_start_date_rides"]
        .ne(alternatives["official_start_date_rides"])
    ].iloc[0]
    end_difference = (
        alternatives["valid_end_date_rides"]
        - alternatives["official_start_date_rides"]
    )
    end_affected_days = int(end_difference.ne(0).sum())
    end_total_absolute_shift = int(end_difference.abs().sum())
    max_end_shift = int(end_difference.abs().max())
    max_end_shift_date = alternatives.loc[
        end_difference.abs().idxmax(), "date"
    ].strftime("%Y-%m-%d")
    out_of_window = int(cleaning_audit["out_of_window"].sum())
    duplicate_ids = int(
        cleaning_audit["duplicate_ids_within_chunk"].sum()
        + cleaning_audit["duplicate_ids_global"].sum()
    )
    return (
        duplicate_ids,
        end_affected_days,
        end_total_absolute_shift,
        invalid_added,
        invalid_day,
        max_end_shift,
        max_end_shift_date,
        naive_total,
        official_total,
        out_of_window,
    )


@app.cell
def _(
    duplicate_ids,
    end_affected_days,
    end_total_absolute_shift,
    invalid_added,
    invalid_day,
    max_end_shift,
    max_end_shift_date,
    merge_audit,
    mo,
    naive_total,
    official_total,
    out_of_window,
):
    _invalid_pct = 100 * invalid_added / invalid_day["official_start_date_rides"]
    mo.md(
        f"""
        ## Decision log

        ### 1. Require valid IDs/timestamps, positive duration, and a 2024 start date

        **Decision.** We excluded trips without the required fields, trips whose
        `ended_at <= started_at`, starts outside 2024, and any repeated `ride_id` before
        daily aggregation.

        **Alternative.** Count every row with a parseable 2024 `started_at`, even when
        its ID/end time/duration fails the validity rule.

        **Evidence.** The official rule kept **{official_total:,}** rides. The executed
        alternative counted **{naive_total:,}**, adding **{invalid_added:,}** records;
        all were nonpositive-duration records on
        **{invalid_day['date'].strftime('%Y-%m-%d')}**. A separate **{out_of_window:,}**
        records in the January archive started outside 2024. Exact within-chunk and
        cross-file auditing found **{duplicate_ids:,}** duplicate ride IDs.

        **Consequence.** The executed alternative would raise the November 3 daily count
        by **{invalid_added:,} rides ({_invalid_pct:.2f}%)** and treat impossible/nonpositive
        durations as valid demand. The chosen rule prevents that contamination.

        ### 2. Assign each ride to its start date

        **Decision.** Daily demand is defined by the New York calendar date of
        `started_at`.

        **Alternative.** Assign each otherwise-valid ride to the calendar date of
        `ended_at`. This alternative was executed for every ride in the same streaming
        pass.

        **Evidence.** Start-date and end-date assignment have the same annual total, but
        **{end_affected_days:,} of 366 daily counts differ**. The sum of absolute daily
        reallocations is **{end_total_absolute_shift:,} rides**; the largest single-day
        change is **{max_end_shift:,} rides on {max_end_shift_date}**.

        **Consequence.** End-date assignment would attach rides crossing midnight to the
        following day's weather and could move a daily point between precipitation
        categories. Start date better represents the conditions when the rider chose to
        begin the trip.

        ### 3. Match to one complete Central Park daily record

        **Decision.** We use NOAA Central Park station `USW00094728` and validate the
        `date` merge as one-to-one.

        **Alternative.** Download several NYC stations and average their daily weather,
        which could reduce dependence on any single station but changes the meaning of a
        rain event.

        **Evidence.** Central Park supplied **{int(merge_audit['weather_raw_rows']):,}**
        rows covering all of 2024, with zero duplicate dates and zero missing `PRCP`,
        `TMAX`, or `TMIN`. The merge matched **{int(merge_audit['weather_dates_matched']):,}
        of {int(merge_audit['calendar_days']):,}** dates and left
        **{int(merge_audit['weather_dates_unmatched']):,}** unmatched.

        **Consequence.** A multi-station average could smooth a localized heavy shower
        into lighter citywide precipitation and move dates among the RQ1 rain bins. The
        selected station preserves an observed, complete series, but the limitation is
        that Central Park is only a proxy for conditions at all trip origins.
        """
    )
    return


if __name__ == "__main__":
    app.run()
