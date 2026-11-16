# M1 feasibility notes

Run date: 2026-10-14

## Source feasibility

- The public Citi Bike S3 archives and NOAA Daily Summaries API were accessible
  without an API key.
- All 12 NYC Citi Bike archives for 2024 were valid ZIP files. They contained 50
  CSV members in total (2–6 per month), and every member exposed the required
  `ride_id`, `started_at`, `ended_at`, and `member_casual` fields.
- Citi Bike timestamps are offset-naive. This project interprets them as New York
  local operating time and assigns demand to the calendar date of `started_at`.
- The NOAA extract contains 366 rows for Central Park station `USW00094728`, one
  for each day of leap year 2024. `PRCP` is millimeters; `TMAX` and `TMIN` are °C.

## Grain and coverage

- Citi Bike input grain: one recorded ride.
- NOAA input grain: one station-date.
- Final analysis grain: one calendar date.
- 44,303,209 raw trip rows were read and 44,302,480 valid 2024 starts retained.
- All 366 final dates matched weather; no one-to-many join or missing weather field
  was found.

## Data-quality findings

- 410 rows in the January archive started outside the 2024 study window.
- 319 November rows had `ended_at <= started_at`; all affected November 3.
- Required-field missingness was zero.
- Exact cross-chunk and cross-file `ride_id` duplicate count was zero.
- Daily demand ranged from 21,571 to 194,315 rides. These extremes were retained
  because they are valid observed days, not impossible values.

## Resolved issues

- The notebook now follows the required order: Data description precedes Data
  manipulation.
- Global ID uniqueness is audited with SQLite rather than only within chunks.
- The submission notebook embeds the verified reduced outputs, avoiding a data-path
  failure when the `.py` file is separated from the raw 8+ GB archive.
- The HTML export executes without cell errors and contains all three figures.

## Group information

Group 11 consists of Yanran Chen (`yanranc`) and Hanyang Liu (`hanyliu`).
