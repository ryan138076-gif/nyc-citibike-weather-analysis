# NYC Citi Bike Ridership and Weather — SI 618 Milestone 1

This project describes how 2024 daily precipitation and temperature are associated
with NYC Citi Bike demand, including weekday/weekend differences. Milestone 1 uses
loading, cleaning, merging, grouping, summarising, and plotting only—no hypothesis
tests, regression, causal inference, or machine learning.

## Submission files

- `SI618_M1_Group_11.py` — final marimo notebook. Its verified reduced outputs are
  embedded so the notebook remains runnable without the 8+ GB raw archive.
- `SI618_M1_Group_11.html` — executed static HTML export with tables and plots
  (a mirror is also kept under `reports/`).

## Sources and terms

- [Citi Bike Trip Histories](https://citibikenyc.com/system-data), published by NYC
  Bike Share / Citi Bike. The [NYCBS Data Sharing Policy](https://citibikenyc.com/data-sharing-policy)
  applies. Twelve NYC monthly ZIPs for 2024 were downloaded on 2026-10-14; `JC-`
  Jersey City archives were excluded.
- [NOAA NCEI Daily Summaries API](https://www.ncei.noaa.gov/access/services/data/v1),
  Central Park station `USW00094728`, `PRCP`, `TMAX`, and `TMIN`, metric units.
  The 2024 extract was downloaded on 2026-10-14. NOAA-produced data are
  [public-domain/CC0](https://data.noaa.gov/docucomp/xmlComponent/show/690447).

## Verified 2024 pipeline result

- 12 Citi Bike ZIPs and all 50 CSV members processed in 200,000-row chunks.
- 44,303,209 raw trip rows read; 44,302,480 valid 2024 ride starts retained.
- 319 nonpositive-duration rows and 410 starts outside 2024 excluded.
- 0 missing required fields, 0 within-chunk duplicate ride IDs, and 0 cross-file
  duplicate ride IDs.
- 366 bike dates and 366 NOAA dates merged one-to-one; 366 matched, 0 unmatched.
- 0 missing `PRCP`, `TMAX`, or `TMIN`; 0 duplicate merged dates.

The pipeline performs exact global ride-ID deduplication through a temporary SQLite
key table, so it does not rely on within-chunk checks alone. Dates with no observed
bike records would remain missing rather than being silently converted to zero.

## Reproduce

```bash
uv venv .venv
UV_CACHE_DIR=.uv-cache uv pip install --python .venv/bin/python -r requirements.txt

# Download and process the complete year from the two official public sources.
.venv/bin/python src/pipeline.py --months 1 2 3 4 5 6 7 8 9 10 11 12 --download

# Inspect/edit and export the notebook.
.venv/bin/marimo edit SI618_M1_Group_11.py
.venv/bin/marimo export html SI618_M1_Group_11.py \
  -o reports/SI618_M1_Group_11.html -f
```

The course-specified export command is also supported:

```bash
UV_CACHE_DIR=.uv-cache uvx marimo export html --sandbox \
  SI618_M1_Group_11.py -o reports/SI618_M1_Group_11.html
```

## Files produced by the pipeline

- `data/processed/daily_bike_weather_2024.csv` — one row per calendar date.
- `data/processed/trip_cleaning_audit.csv` — chunk-level cleaning evidence.
- `data/processed/source_inventory.csv` — every ZIP/CSV member and row count.
- `data/processed/merge_audit.csv` — date coverage, matched/unmatched counts, missingness.
- `data/processed/data_description.csv` — computed types, units, and missingness.
- `data/processed/decision_alternatives.csv` — executed alternatives used by the
  decision log (naive validity rule and trip end-date assignment).

Raw and processed data remain ignored by Git because the Citi Bike source files are
large and the data-use policy restricts redistribution as a stand-alone dataset.

## Limitations

- Central Park is a complete but single-station proxy for weather across the city.
- `(TMAX + TMIN) / 2` is a temperature proxy, not a true hourly daily mean.
- Weather associations are unadjusted for season, holidays, system growth, events,
  or other factors and must not be interpreted causally.
