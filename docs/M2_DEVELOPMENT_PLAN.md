# SI 618 Milestone 2 — Development Plan

**Project:** Weather and NYC Citi Bike Ridership in 2024  
**Group:** 11 — Yanran Chen (`yanranc`), Hanyang Liu (`hanyliu`)  
**Repository:** https://github.com/ryan138076-gif/nyc-citibike-weather-analysis  
**Document version:** 1.1 · 2026-11-15  
**Milestone deadline:** Monday, November 16, 2026, **before 3:30 PM (America/Detroit)**  
**Status:** Development specification; analysis results are **not** yet computed.

> **Scope note.** This is a repository-ready specification based on the group's M1 notebook/pipeline, M1 instructor feedback, the November 11 discussion, and the official M2 rubric. v1.1 reconciles the plan with a local checkout of the repository (`main` @ `07e0849`): paths in §4 now describe the **actual** tree plus the minimum new files.

### Changes in v1.1

- §4 paths reconciled with the real repository; the build is reduced to an extension of `src/pipeline.py` plus one weather script.
- §2.1 / §5 / §6.1: the 319 M1 "nonpositive-duration" rows all fall on **2024-11-03 (fall DST)**; ambiguous/non-existent DST hours get an explicit policy (NaN, never zero).
- §6.2: NOAA LCD hourly Central Park observations added as an equal candidate to Open-Meteo (decision-log page example warns against smoothed rain); Open-Meteo `precipitation` is a **preceding-hour sum** → explicit one-hour alignment; request in GMT; wet-hour threshold.
- §9: evidence written as live marimo f-strings; missing Response to feedback lowers the decision log one level.
- §3 / §8: response to feedback now quotes the instructor's "otherwise alike" request and records the declined "earlier years" option.
- §7 (aligned with the official M2 rubric): one OLS regression per question on `log(rides + 1)`, controls `hour × weekend`, within-quarter contrasts via `rain × quarter` with Holm; independence handled by the rubric's two routes (explain the dependence + re-test on an independent one-row-every-second-day subset); effect size and practical significance first; extra sensitivity analyses removed unless they feed the decision log; RQ-revision rationale added (§7.0).
- §11 / §12 / §13: missing dependencies (`scipy`, `statsmodels`), embedded hourly data for the Canvas `.py`.

## 1. Objective and scope

M2 must **answer the same three M1 research questions** using appropriate statistical analysis from SI 618 Topics 04–07, while directly improving two issues raised by the teaching team: seasonal confounding and limited daily sample size. The agreed direction is to **convert ridership and weather analysis to hourly resolution** and **compare rainy and dry conditions within four calendar quarters**.

**Deliverables:** (1) a reproducible hourly merged dataset and audits; (2) a marimo notebook with the official sections, statistical results and interpretations; (3) a checked HTML export; (4) three evidence-based M2 analysis decisions. **Out of scope for M2:** classifiers, clustering, predictive machine-learning evaluation, and causal claims. Keep M3 extension opportunities separate from M2 conclusions.

**Primary success criterion:** every research question has a justified method, documented assumption checks (especially time dependence), test statistic, p-value when applicable, effect size, sample size, clear plot if helpful, and a plain-language answer with limitations.

## 2. Inputs and source-of-truth hierarchy

| Source | Role | Current status |
|---|---|---|
| `SI618_M1_Group_11.py` (repo root) | M1 question wording, data story, visuals and notebook conventions (daily table embedded as base64) | In repo |
| `src/pipeline.py` | Implemented M1 cleaning, exact ID deduplication, daily grouping, NOAA joining and audits | In repo; inspected |
| `SI618_M1_Group_11.html` (root, mirrored in `reports/`) | Reader-facing M1 presentation | In repo |
| `reports/feasibility-notes.md`, `data/processed/*.csv` | M1 audit results (row counts, exclusions, merge audit) | In repo |
| Official [M2 rubric](https://github.com/cteplovs/si618-fa2026-student/blob/main/project/milestone-2.md) | Mandatory headings, statistics, 200-point grading and submission | Checked |
| Official [decision-log rules](https://github.com/cteplovs/si618-fa2026-student/blob/main/project/decision-log.md) | Three M2 decisions, evidence and demonstrated alternative | Checked |
| M1 feedback + November 11 studio discussion | Approved changes and meeting response | Supplied in conversation |
| [Citi Bike System Data](https://citibikenyc.com/system-data) | Source of official 2024 monthly ride archives (8+ GB) | **Not present locally** (`data/raw/citibike/` is git-ignored and absent); must be re-downloaded with `src/pipeline.py --download` |
| NOAA daily Central Park station `USW00094728` | M1 baseline weather and aggregate-level cross-check | Used by M1 pipeline |
| [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api) | Proposed hourly temperature/precipitation source | Candidate; must be fetched and quality-checked |

### 2.1 What the current M1 pipeline actually does

- Reads every CSV member of each monthly Citi Bike ZIP **in 200,000-row chunks**.
- Requires the columns `ride_id`, `started_at`, `ended_at`, and `member_casual`.
- Removes missing ride IDs/timestamps; excludes trips whose `ended_at <= started_at`; excludes starts outside 2024; retains only the first instance of any `ride_id` using chunk-level and **SQLite global deduplication**.
- Reports invalid membership categories in an audit; when computing member/casual totals, only recognized `member` and `casual` categories enter those subtotals. **Do not infer** that the current code removes invalid categories from overall ride counts.
- Attributes every qualifying trip to its **start** date. Cross-midnight trips with a positive duration remain valid.
- Aggregates to calendar days and joins NOAA **daily summaries** (`PRCP`, `TMAX`, `TMIN`) from Central Park, station `USW00094728`.
- Generates cleaning, inventory, merge and decision-alternative audits.

**M1 audit facts relevant to M2** (from `README.md` and `reports/feasibility-notes.md`): 44,303,209 raw rows → 44,302,480 valid 2024 starts; 410 out-of-window starts; **319 nonpositive-duration rows, all on 2024-11-03**; 0 duplicate IDs; Citi Bike timestamps are **offset-naive** and interpreted as New York local time.

**DST finding.** 2024-11-03 is the fall DST change (01:00–01:59 occurs twice). With offset-naive timestamps, a ride that starts in the first 01:xx (EDT) and ends in the repeated 01:xx (EST) *appears* to end before it starts. The 319 exclusions are therefore very likely **valid rides misclassified by the DST artifact**, not data errors. M2 keeps the M1 rule for the primary analysis (preservation rule below) but reports this explanation and, optionally, a sensitivity count that re-admits these rows by adding one hour to `ended_at`. The impact (319 of 44.3 M) is negligible for the analysis but worth stating in the cleaning narrative.

**M2 preservation rule:** keep the M1 ride-validity rules and global uniqueness unless a documented, evidenced M2 decision explicitly revises them. Change the aggregation grain and weather source transparently; do not silently change the eligible-trip population.

## 3. Decisions from feedback and meeting

| Feedback or discussion | Agreed M2 response | Documentation expected in notebook |
|---|---|---|
| Rain, temperature and rides all vary by season; instructor asked how we will compare rainy and dry periods "that are otherwise alike" | Compare precipitation/ridership **within Q1, Q2, Q3 and Q4** in addition to any pooled result, **and** hold other regular demand drivers fixed: hour of day × weekday/weekend, temperature (see §7) | Four-quarter comparison table/plot; list explicitly which "otherwise alike" conditions are controlled and which are not (holidays, events, system growth within a quarter) |
| One year of daily observations has just 366 rows ("small for Milestone 3"); instructor offered two options: **add earlier years** (also enables testing on an unseen year) **or model by hour** | Use **hourly ridership and hourly weather** to obtain a richer time series; **earlier years considered and deferred** (keeps M1 continuity and fits the M2 timeline; a held-out earlier year is noted as an M3 extension) | Describe hourly construction and dependence; **more rows do not imply more independent observations**; name the declined alternative and why |
| M2 should show cleaning code or main steps "so that a reader can see how the daily table was built" | Include a clear, concise, executable explanation of M1 cleaning **and** of the new hourly table, linking to `src/pipeline.py` | Cleaning-code excerpts or functions plus live audits in notebook; show that hourly totals reproduce the M1 daily table |
| Studio question about cross-day rides | **Attribute positive-duration cross-midnight rides to the hour in which `started_at` occurs** | Include a concrete start/end example, rationale, and evidence of the count effect if compared with end-time attribution |
| Studio decisions included hour-level and four-quarter analyses | Preserve these in the study design | In feedback section: record the exact decision discussed, explanation given and whether the discussion changed the team's view |

**Timestamp correction:** a trip starting before midnight and ending after midnight normally has `ended_at > started_at`, **not** `started_at > ended_at`. A record with `started_at > ended_at` is a *negative-duration/invalid* record and remains excluded under M1 cleaning. Example: a ride from `2024-06-30 23:50` to `2024-07-01 00:10` belongs to `2024-06-30 23:00` (New York local time). (The studio discussion was recorded informally as "`starttime > endtime` (cross-day)"; the notebook must use the corrected wording above.)

**Meeting detail still to confirm before final narrative:** the precise verbal explanations provided for each discussed M1 decision and whether your view changed. The three high-level items above are known, but do not fabricate quotations or claim the teaching team explicitly approved a particular weather provider.

## 4. Repository organization

Actual tree at `07e0849`, with the **minimum** M2 additions marked `+`. The M1 layout (notebook at the root, HTML mirrored in `reports/`) is kept rather than introducing `notebooks/`, `exports/` or `tests/` directories; the hourly build is an extension of the existing pipeline, not a new module set.

```text
nyc-citibike-weather-analysis/
├── README.md                       # update: add M2 section + reproduce commands
├── requirements.txt                # update: + scipy, statsmodels
├── .gitignore                      # already ignores data/raw/citibike/
├── SI618_M1_Group_11.py / .html
├── + SI618_M2_Group_11.py          # Canvas-named notebook (root, like M1)
├── + SI618_M2_Group_11.html
├── docs/
│   ├── M1_DEVELOPMENTS.md
│   └── + M2_DEVELOPMENT_PLAN.md    # this file
├── src/
│   ├── pipeline.py                 # + `--grain hourly`: hourly counts, DST audit
│   ├── + fetch_hourly_weather.py   # NOAA LCD + Open-Meteo requests, archived raw files
│   └── + validate_hourly.py        # acceptance gates of §6.4 as assertions
├── data/
│   ├── raw/
│   │   ├── citibike/               # ignored; re-download (8+ GB)
│   │   └── weather/
│   │       ├── noaa_2024.csv
│   │       ├── + noaa_lcd_2024.csv
│   │       └── + open_meteo_2024_hourly.json  (+ request metadata)
│   └── processed/
│       ├── daily_*.csv, *_audit.csv, ...      # M1 outputs, unchanged
│       ├── + hourly_bike_2024.csv
│       ├── + hourly_weather_2024.csv
│       ├── + hourly_bike_weather_2024.csv
│       ├── + hourly_dst_audit.csv
│       └── + weather_source_comparison.csv   # LCD vs. Open-Meteo
└── reports/
    ├── feasibility-notes.md
    └── SI618_M1_Group_11.html
```

The official naming template is `SI618_M2_<group name>`; use `Group_11` consistent with M1. Avoid committing large raw data, SQLite temporary files, cache directories, secrets or API credentials. Include small, reproducible derived artifacts only if repository size and course policies permit.

## 5. Hourly data contract

**Observation unit:** one **actual elapsed hour** of 2024 in New York. `hour_start_utc` is the unique primary key; `hour_start_local` is a timezone-aware display/grouping label.

| Column | Type / semantics | Notes |
|---|---|---|
| `hour_start_utc` | timezone-aware UTC timestamp | Unique join key; use ISO 8601 with offset when serialized |
| `hour_start_local` | timezone-aware `America/New_York` timestamp | Retain UTC offset for DST ambiguity |
| `date_local` | local calendar date | For quarterly and daily validation |
| `hour_of_day` | integer 0–23 | Repeated 01:00 hour during fall DST is allowed |
| `month` | integer 1–12 | Derived from local date |
| `quarter` | Q1 / Q2 / Q3 / Q4 | Calendar quarters, not meteorological seasons |
| `day_of_week` | integer 0–6 | Mon=0 |
| `is_weekend` | Boolean | Sat/Sun |
| `hourly_rides` | nonnegative integer / NaN | Valid unique rides **starting** in the hour; **NaN for the two DST-ambiguous fall hours** (§6.1) — never 0 |
| `dst_flag` | none / spring_gap / fall_ambiguous | Marks the hours affected by DST handling |
| `member_rides` | nonnegative integer | Member subset |
| `casual_rides` | nonnegative integer | Casual subset |
| `temperature_c` | numeric / NaN | Hourly weather; source and method documented |
| `precipitation_mm` | numeric / NaN | Accumulation over **[hour_start, hour_start + 1 h)** — the same interval in which the counted rides start. For Open-Meteo this is the value stamped at `hour_start + 1 h`; for NOAA LCD the routine report closing that hour (≈ :51), after converting LST to UTC (§6.2) |
| `is_rainy` | Boolean / missing | Primary: `precipitation_mm ≥ 0.2`; sensitivity: `> 0` (reanalysis produces many 0.1 mm "drizzle" hours, see §6.2). Missing when precipitation missing |
| `rain_category` | no rain / light / heavier / missing | Candidate M1-compatible bins: 0, (0,5], >5 mm **per hour**; interpret carefully |
| `weather_source` | string | `noaa_lcd` or `open_meteo` + model; provenance |

**Important comparability caveat:** M1's >5 mm threshold was **daily** rainfall. Reusing `>5 mm` on **hourly** rainfall changes its meaning substantially. Preserve a binary dry/wet primary analysis and, if using categorical rain intensity, inspect hourly frequency and justify bins explicitly. Do not describe daily and hourly thresholds as interchangeable.

**2024 target:** 366 days × 24 = **8,784 elapsed hours**. This holds across the two New York DST changes because the spring day has 23 elapsed hours and the fall day 25. Do not create a naive local timestamp index and drop one of the repeated fall hours. A complete hourly grid should be constructed first in UTC, then converted to `America/New_York` for grouping. Store source timestamps and verify their semantics rather than applying an arbitrary hourly shift.

**Analysis rows:** 8,784 grid rows − 2 DST-ambiguous hours (bike count unknown) − any hours with missing weather. Report this N per research question.

## 6. Data engineering implementation

### 6.1 Stage A — Citi Bike hourly aggregator

**Implementation choice:** add `--grain hourly` to `src/pipeline.py` instead of writing a new module. The cleaning loop stays byte-for-byte the same; only the counting key changes from `started_at.dt.normalize()` (date) to `started_at.dt.floor("h")` (naive local hour), for total, member and casual counters. This makes the daily reconciliation test (below) hold by construction and keeps the eligible-trip population identical to M1.

1. Reuse the 2024 official monthly ZIP retrieval and all-CSV-member streaming pattern in the M1 pipeline. **The raw ZIPs are not on disk; start the `--download` run first, in the background**, since it gates all later work.
2. Parse both times and retain existing eligibility checks (`ride_id`, valid timestamps, strictly positive duration, start within calendar 2024, global deduplication).
3. **DST policy for offset-naive Citi Bike timestamps** (feasibility notes confirm they carry no offset):
   - **Fall, 2024-11-03 01:00–01:59 local** occurs twice (EDT then EST). A naive timestamp cannot say which one, so all those rides land in one naive `01:00` bucket. Policy: set **both** elapsed hours (`05:00Z` and `06:00Z`) to `hourly_rides = NaN`, `dst_flag = fall_ambiguous`, and report the combined naive count in `hourly_dst_audit.csv`. Do **not** assign the combined count to one hour and zero-fill the other — that would create a fake doubled hour and a fake empty hour. Cost: 2 of 8,784 hours.
   - **Spring, 2024-03-10 02:00–02:59 local** does not exist. Count any ride starts with a naive `02:xx` stamp on that date, report the number, and exclude them (expected ≈ 0). The grid has no such hour, so nothing is zero-filled.
   - Do not use `tz_localize(..., ambiguous='infer')` on unsorted trip records.
4. Assign each valid ride to the hour containing `started_at` (New York local); localize the hourly *keys* (not the 44 M trips) with `ambiguous`/`nonexistent` handled per item 3, then convert to `hour_start_utc`.
5. Aggregate total rides plus `member` and `casual` subset counts. Preserve unmatched membership counts as an audit rather than assuming `hourly_rides == member_rides + casual_rides` under all circumstances.
6. Join counts to a complete **8,784-hour** calendar grid; fill missing bike-count hours with **0** only after confirming those hours are in study coverage (never the DST-flagged hours). Do not fill weather missing values with zero.
7. Persist audit totals for excluded rows, invalid durations, duplicates and cross-midnight ride counts; also the count of the 319 nonpositive-duration rows whose start and end both fall in 2024-11-03 01:xx (DST explanation, §2.1).

**Regression test:** summing hourly valid rides by naive local date (DST-flagged hours included via the audit count) must reproduce `data/processed/daily_bike_2024.csv` **exactly**, because the cleaning code and the attribution rule are unchanged. Any difference is a bug, not a policy effect.

### 6.2 Stage B — Hourly weather source selection

**Two candidates, compared before choosing.** The official decision-log page's worked example is exactly this project's situation (hourly bike trips matched to Central Park weather) and argues *against* smoothing: averaging sources "turns short, heavy showers into longer spells of light rain, which weakens the drop in ridership during rain". A reanalysis grid cell is itself spatially and temporally smoothed, so it is not automatically the better source.

| | A. NOAA LCD hourly, Central Park (station `USW00094728`, same station as M1) | B. Open-Meteo Historical Weather API (reanalysis) |
|---|---|---|
| Measurement | Station gauge observation; continuity with M1's NOAA daily data | Model/reanalysis grid cell at ≈ 40.78, −73.97 |
| Time grid | Irregular report times (routine hourly reports near :51, plus specials); times in **local standard time** (no DST shift) | Regular hourly grid; request **`timezone=GMT`** |
| Precipitation | `HourlyPrecipitation` in **inches**; `T` = trace; suffix flags (e.g. `s` suspect) must be parsed; blanks are missing, not 0 | `precipitation` in mm, preceding-hour sum; no gaps expected |
| Main risk | Gaps/special reports need cleaning and a rule to assign reports to clock hours | Smoothing: drizzle hours, weaker/shifted peaks |

**Decision rule:** fetch both. Build the LCD hourly series by assigning each routine report to the clock hour it closes (e.g. a 13:51 report → hour 13:00–14:00), converting inches to mm, trace to a small positive flag (not 0), and leaving missing as NaN. Choose **A** if its hourly coverage of 2024 is high (target ≥ 95 % of hours, gaps not concentrated in one quarter); otherwise **B**, with A's comparison kept as evidence. Either way, report the comparison (share of hours where the two disagree on wet/dry, correlation of hourly precipitation, daily totals vs. M1's NOAA daily `PRCP`). Confirm the LCD access endpoint and station identifier at fetch time. This choice is a strong decision-log candidate (§9) because it is the rubric's own example and changes the wet/dry classification directly.

Open-Meteo request details (if B is used or compared): request in GMT, not `America/New_York` — local-time responses are offset-naive and repeat/skip an hour at the DST changes, which recreates the problem of §6.1. Convert to New York time ourselves.

Implementation checkpoints:

- Fetch **2024-01-01T00:00 local through 2024-12-31T23:00 local** — i.e. 2024-01-01 05:00Z to 2025-01-01 05:00Z, plus one extra hour for the alignment shift below — capturing URL/query parameters, fetch date, model, location, units and timezone. Archive the raw JSON under `data/raw/weather/`.
- Verify all 8,784 physical hours are represented exactly once after conversion to `hour_start_utc`.
- **Precipitation interval.** Open-Meteo documents hourly `precipitation` as the **sum over the preceding hour**: the value stamped `14:00` covers 13:00–14:00. Rides are attributed to the hour they *start* (13:00–14:00 → `hour_start = 13:00`). Therefore `precipitation_mm(hour_start) = API value at hour_start + 1 h`. `temperature_2m` is an instantaneous value at the timestamp; use the value at `hour_start` (or the mean of `hour_start` and `+1 h`) and state which. **Confirm this convention against the current API docs at fetch time and record the doc text in the metadata.** Spot-check with a known 2024 storm (e.g. compare the hour the rain starts with the hour ridership drops).
- **Wet-hour threshold.** Reanalysis precipitation is spatially smoothed and yields many 0.1 mm hours that a station gauge would record as dry or trace. Inspect the distribution of hourly values; use `≥ 0.2 mm` as the primary wet definition and `> 0` as a sensitivity check (a decision-log candidate, §9).
- Quantify missing values, repeated timestamps, negative precipitation, implausible temperature and quarter-by-quarter coverage.
- Compare **daily aggregates** of the hourly candidate weather with M1's NOAA Central Park daily summary (rain accumulation, broad temperature patterns). NOAA first-order daily values are summed over the **local standard-time** day (midnight–midnight LST, i.e. 01:00–01:00 EDT in summer), so sum the hourly series over the same window before comparing. Stations/models differ, so this is a plausibility check (report correlation and wet/dry-day agreement), **not** a requirement for exact equality.
- If unacceptable gaps or temporal ambiguity arise, switch to an audited NOAA hourly source or document and justify another method; never fabricate missing rain measurements.

### 6.3 Stage C — Hourly merge and features

1. `validate='one_to_one'` on `hour_start_utc`; retain an explicit merge indicator or audit summary.
2. Verify unique hourly keys and 8,784 calendar rows; report bike-only and weather-only hours, actual weather completeness, and rows used by each research question.
3. Derive calendar quarter, hour-of-day, day-of-week, weekend flag, binary rain and carefully justified rain-intensity bins.
4. Do not interpolate precipitation as if known; distinguish **dry** (`0`) from **missing** (`NaN`). If temperature interpolation is considered, report its extent and compare sensitivity.
5. Save processed outputs and compact source/processing metadata sufficient for independent reruns.

### 6.4 Data integrity tests / acceptance gates

| Test | Acceptance condition |
|---|---|
| Hour coverage | 8,784 unique elapsed-hour keys spanning 2024 NYC local calendar year |
| DST | 23-hour spring-transition day; 25-hour fall-transition day; no duplicate UTC keys; the two fall-ambiguous hours are NaN (not 0) and their combined naive count is in the audit; spring-gap ride starts counted and reported |
| Ride attribution | Every valid ride counted exactly once at its start hour; cross-midnight example passes |
| Duration | `ended_at <= started_at` excluded; positive-duration cross-midnight rides retained |
| Deduplication | No duplicate accepted `ride_id` across chunks, CSV members or months |
| Daily reconciliation | Hourly totals aggregated to local date equal `daily_bike_2024.csv` exactly (366/366 dates) |
| Weather | Rain 0 not confused with missing; precipitation units and hour interval documented; one-hour alignment shift applied and spot-checked |
| Join | One-to-one keys; missing weather and effective sample sizes explicitly reported |
| Reproducibility | Independent rerun obtains the same processed outputs from pinned inputs/settings |

## 7. Statistical analysis plan for three research questions

**Rubric constraints that shape this section** (official M2 page): methods come from topics 04–07 (descriptive statistics and plots, correlation, t-tests, ANOVA, linear regression, contingency tables/chi-square); "we will grade how well you answer your questions, not how many techniques you use"; every test in topics 05–06 assumes independent rows, so dependent data must either be tested on an independent version of the data or the effect of dependence on the p-value must be explained; with many rows "the answer depends on the effect size, and on whether it is big enough to matter". Hence: **one primary linear regression per question, one independent-subset check, effect size first**, and only the alternatives that feed the decision log.

### 7.0 Research-question wording

Restate the three M1 questions verbatim, each with its columns, then the hourly operational wording. The rubric accepts a revision made because the data could not answer the question, not one made to get a more interesting answer. The reason to give is therefore: *the instructor's feedback showed that the daily version cannot compare rainy and dry periods that are otherwise alike — 366 days split into four quarters and wet/dry leaves too few comparable days, and a daily total mixes rainy and dry hours — so the same questions are asked at hourly resolution.* The substance of each question (precipitation association; temperature nonlinearity; weekday/weekend difference) does not change. Say this before any results are shown.

### 7.1 Shared modelling framework (applies to Q1–Q3)

Fixed **before** looking at results, so the three questions use one model family and the analysis does not become a specification search.

- **Method: ordinary least-squares linear regression** (topic 06), fitted with `statsmodels.formula.api.ols`. Group comparisons that a regression adjusts for are also shown descriptively (medians, cell Ns, plots).
- **Outcome: `log(hourly_rides + 1)`.** Hourly demand varies more than tenfold between 4 AM and the evening peak, and rain plausibly removes a *share* of riders rather than a fixed number. On the raw scale the same "−300 rides/hour" means very different things at 4 AM and 6 PM, and residual spread grows with the level. On the log scale `100 × (exp(b) − 1)` is a "% change in rides", comparable across hours and quarters. Back-transform to rides/hour at typical hours for readers.
- **"Otherwise alike" controls** (instructor's wording): `C(hour_of_day) × is_weekend` (weekday commute peaks vs. weekend midday profile — without this, rain is confounded with *when* it falls), `C(quarter)`, and centred temperature with its square (from Q2) in Q1/Q3.
- **Within-quarter comparisons:** `is_rainy × C(quarter)` gives each quarter its own rain effect. Four planned quarter contrasts → **Holm adjustment**, stated in the Result. A `C(quarter)` intercept alone is *not* a within-quarter comparison.
- **Independence assumption — how it is handled** (the rubric's two options, both used):
  1. *Explain:* consecutive hours of the same day share weather, events and demand shocks, so the full-data regression treats ~8,700 correlated rows as if independent; its standard errors are too small and its p-values too optimistic. Show the evidence: lag-1 and lag-24 autocorrelation of the residuals. Interpret the full-data result through its **effect size**, not its p-value.
  2. *Test on an independent version:* the **independent subset** = one row per day at a fixed hour (17:00, the weekday evening peak, also a busy weekend hour), using **every second day** (≈ 183 rows). Re-fit the question's model with the controls that still vary in the subset (`is_rainy`, `is_weekend`, `C(quarter)`, temperature). Check the subset's own residual lag-1 autocorrelation to show it is close to zero. Report its statistic, p-value and effect size next to the full-data estimate. This subset has little power — wet 17:00 hours may number only a dozen or two, so report that N — and its role is to confirm direction and rough size with a p-value that does not rest on independent hours, not to replace the full-data effect size.
- **Practical significance:** every Answer states whether the effect matters in practice, translated into rides (e.g. "−X% ≈ Y fewer rides per hour at the weekday evening peak, out of Z").

### Q1 — How is precipitation associated with Citi Bike ridership?

**Columns:** `hourly_rides`, `precipitation_mm`, `is_rainy`, `quarter`, `hour_of_day`, `is_weekend`, `temperature_c`.

- **Approach:** describe wet/dry hourly ridership by quarter (cell Ns, medians, plot). Model: `log(rides+1) ~ is_rainy × C(quarter) + C(hour) × is_weekend + temp_c + temp_c²`; pooled rain effect from the same model without the quarter interaction. Holm-adjust the four quarter-specific rain effects. Independent-subset check as in §7.1.
- **Result:** t statistic, p-value (Holm-adjusted for quarters), % change in rides in wet vs. dry hours per quarter and pooled with 95% CI, N per quarter and wet/dry cell; subset estimate alongside.
- **Assumptions:** residual-vs-fitted plot (constant spread), residual histogram/Q-Q (approximate normality — less critical at this N), influential hours (storms, holidays), residual autocorrelation (§7.1).
- **Interpretation:** association within quarters does not remove within-quarter confounding (holidays, events, storms, system growth); one city, one year.

### Q2 — Is the temperature–ridership relationship nonlinear?

**Columns:** `hourly_rides`, `temperature_c`, `hour_of_day`, `quarter`, `is_weekend`, `is_rainy`.

- **Approach:** fit linear-temperature and quadratic-temperature regressions (temperature centred before squaring) on the **same rows** with `C(hour) × is_weekend + C(quarter) + is_rainy` controls. The test is the t-test of the squared term. Hour controls are essential because temperature tracks time of day (afternoons are warmer); without them the curve partly re-describes the daily demand cycle. Independent-subset check as in §7.1.
- **Result:** squared-term coefficient, t, p-value, N; fitted % difference in rides between observed temperatures (e.g. 5 °C vs 15 °C vs 25 °C); turning point if the curve bends; change in adjusted R²; fitted curve with 95% band over the observed range only.
- **Assumptions:** residual diagnostics as in Q1; centring removes most of the collinearity between temperature and its square.
- **Interpretation:** a significant squared term does not establish a causal temperature effect or an exact optimum; report the curve shape only where the data support it.

### Q3 — Does the precipitation–ridership association differ between weekdays and weekends?

**Columns:** `hourly_rides`, `is_rainy`, `is_weekend`, `quarter`, `hour_of_day`, `temperature_c`.

- **Approach:** describe weekday/weekend × wet/dry medians and cell Ns. Model: Q1's model with `is_rainy × is_weekend` added (it already contains `C(hour) × is_weekend`, so the interaction is not just the different daily profiles). The test is the t-test of the interaction term. Wet weekend hours are the sparsest cell — report its N. Independent-subset check as in §7.1.
- **Result:** interaction coefficient, t, p-value, N; effect size as the rain response on each day type ("−X% on weekdays vs. −Y% on weekends") with CIs. Note that absolute rides/hour can tell a different story (weekday peaks are larger), and give one back-transformed example.
- **Assumptions:** as Q1; sparse cells make the interaction less precise.
- **Interpretation:** an interaction association does not show that rain causes a distinct weekend response (weekend trips differ in purpose, rider mix and timing).

### Cross-question reporting template

For **each** of Q1–Q3 the notebook shows:

1. **Approach:** method + why it suits the question and data; assumptions, how each is checked in the notebook, and what was done about any that fail (independence: §7.1).
2. **Result:** test statistic, p-value, effect size with units, N actually used, plot, Holm adjustment where several tests answer one question, independent-subset estimate.
3. **Answer:** 2–3 plain sentences with a specific number and whether the effect is big enough to matter, then what the result does not show.

Keep extra analyses out unless they are one of the three decision-log alternatives (§9).

## 8. Required marimo notebook order

Use the **exact required section titles and order**:

```text
# Title and group
## Response to feedback
## Research questions
## Question 1: [full question]
### Approach
### Result
### Answer
## Question 2: [full question]
### Approach
### Result
### Answer
## Question 3: [full question]
### Approach
### Result
### Answer
## Summary of findings
## Decision log
```

The notebook must load and merge its analysis data itself, or transparently load an output from a documented pipeline, explaining **exactly how that file was constructed**. Include concise cleaning-code stages and computed audit summaries. The notebook should remain comprehensible to a classmate who knows SI 618 methods but has not seen M1. Use marimo's reactive computation for dynamically updated results rather than hard-coded analysis numbers.

### Response-to-feedback draft checklist

- Canvas: strong M1 proposal — acknowledge without treating praise as a requested change.
- Canvas: seasonal confounding — quote the request to compare periods "that are otherwise alike"; answer with four-quarter wet/dry comparisons **plus** the hour × weekend and temperature controls; state what remains uncontrolled.
- Canvas: 366 daily rows — hourly representation with dependence handling and hour-specific weather; name the instructor's other option (earlier years / held-out year), say why it was deferred and that it is planned for M3.
- Canvas: display cleaning — M1 cleaning pipeline and new hourly steps visible; show the hourly-to-daily reconciliation against the M1 daily table.
- Cleaning narrative: the 319 excluded "nonpositive-duration" rows are a fall-DST artifact (§2.1); the two ambiguous hours are left missing.
- Studio: start-time rather than end-time attribution — explanation and handling of cross-midnight/invalid durations.
- Studio: hour-level decision — how the group justified it and whether it changed their view.
- Studio: four-quarter decision — how the group justified it and whether it changed their view.
- Capture any additional studio questions verbatim **only if actually remembered/documented**.

### Summary of findings

Approximately **200 English words**, no code or statistical jargon. Provide one direct answer and **one representative number for each question**, then the most important real limitation (for example, one city/year and correlated hourly observations). Draft after the final results have been computed.

## 9. Three M2 decision-log entries

These must concern **analysis choices**, not merely repeat M1 cleaning decisions. Each entry requires **Decision / Alternative / Evidence / Consequence**, with numbers actually generated by the notebook. At least **one consequence must be demonstrated by running the alternative** to reach the 20-point rubric level.

**Keep the evidence live** (official decision-log page). Every number in an entry — and in the Result/Answer text and the Summary — is computed, never typed: write the markdown as a marimo f-string fed by the analysis cells, e.g.

```python
mo.md(f"""
**Evidence.** With wet defined as ≥ 0.2 mm, {n_wet:,} of {n_hours:,} hours
({n_wet / n_hours:.1%}) are wet; with > 0 mm the share rises to {share_any:.1%}.
**Consequence.** Using > 0 mm changes the pooled rain effect from
{eff_main:+.1%} to {eff_alt:+.1%}.
""")
```

If the data or a cleaning rule changes upstream, the log updates with it. The alternative's model is actually fitted in a cell so the Consequence is *shown*, not described.

**Grading coupling:** the decision-log page states that in Milestones 2 and 3 a **missing Response to feedback lowers the decision log by one level**, so the feedback section protects two rubric items, not one.

| Candidate decision | Genuine alternative | Live evidence to compute | Demonstrated consequence |
|---|---|---|---|
| Q1: compare wet/dry hours within quarters | Pooled, unadjusted all-year wet/dry comparison | Quarter-specific and pooled effect estimates | Run both specifications; show how rain effect estimates change |
| Q2: include centered squared temperature term | Linear-only temperature effect | Quadratic term, fit measures, residual plot, fitted curve | Run both models and show numerical/visual difference |
| Q3: include rainfall × weekend interaction | Model only additive rain and weekend effects | Interaction coefficient, p-value, fit comparison and group contrasts | Compare predicted weekday/weekend rain contrasts with/without interaction |
| Transformation: `log(rides+1)` outcome | Raw rides/hour outcome | Residual-vs-fitted spread, rain effect at 04:00 vs. 17:00 under each scale | Fit both; show the raw-scale model's fan-shaped residuals and hour-inconsistent effects |
| Data source: station (NOAA LCD) vs. reanalysis (Open-Meteo) hourly rain | The other source | Hourly coverage; share of hours where the sources disagree on wet/dry | Re-run Q1 with the other source; show how the rain effect changes |
| Subset: wet hour = `≥ 0.2 mm` | wet hour = `> 0 mm` | Share of hours classed wet under each rule; histogram of hourly precipitation | Re-run Q1 with `> 0`; show how many hours move and how the rain effect changes |
| Assumption: independence handled by explanation + independent subset (one 17:00 row every second day) | Report full-data p-values as if hours were independent | Residual lag-1/lag-24 autocorrelation in full data vs. subset | Show full-data and subset estimates, SEs and p-values side by side |

The rubric asks for entries "drawn from your analysis: which test you chose, which subset you compared, which transformation you applied, or how you handled an assumption that did not hold". Pick the **three most informative** of these candidates (the last three map directly onto that list), not predetermined conclusions. If the data favor an alternative, document the actual selection. Do not invent evidence values before analysis.

## 10. Execution plan

| Phase | Implementation tasks | Concrete exit artifact | Priority |
|---|---|---|---|
| P0 — Environment | Verify repo access, project root, dependencies, input availability | Runnable environment; path map | Critical |
| P1 — Data | Reuse M1 streaming cleaning; produce timezone-safe hourly ride series; retrieve and assess hourly weather | Hourly CSVs and cleaning/weather audits | Critical |
| P2 — QA | DST tests, 8,784-hour grid, ID dedup, local-daily reconciliation, missingness, merge checks | Validation report with pass/fail results | Critical |
| P3 — Statistics | Q1–Q3 diagnostics, planned tests, effect sizes, charts, quarter comparisons, sensitivity checks | Live statistical outputs | Critical |
| P4 — Notebook narrative | Exact headings, feedback, clear RQ answers, 200-word summary, three decision entries | `SI618_M2_Group_11.py` | Critical |
| P5 — Export / review | Re-run cleanly, export HTML, open and check all outputs, cross-check numbers and naming | `SI618_M2_Group_11.html` and Canvas-ready pair | Critical |
| P6 — M3 backlog | Note future multi-year holdout or predictive methods without adding ML to M2 | Short future-work paragraph | Optional |

## 11. Dependencies and repeatable commands (proposed)

Packages: `pandas`, `numpy`, `matplotlib`, `marimo` (already in `requirements.txt`) **plus `scipy` and `statsmodels`, which are currently missing** and must be added to `requirements.txt` and to the notebook's inline `--sandbox` script metadata. Python `urllib` suffices for HTTP. Pin tested versions after the first successful run.

Commands (the `--grain` flag and the two new scripts are design targets, not yet implemented):

```bash
# Bike: re-download 2024 ZIPs and build hourly counts (long-running; start first).
python src/pipeline.py --months 1 2 3 4 5 6 7 8 9 10 11 12 --download --grain hourly

# Weather + merge + gates.
python src/fetch_hourly_weather.py
python src/validate_hourly.py

# Notebook (repo root, like M1).
marimo edit SI618_M2_Group_11.py

# Official export command (run from the repo root):
uvx marimo export html --sandbox SI618_M2_Group_11.py -o SI618_M2_Group_11.html
```

**Data access in the submitted notebook:** Canvas receives only the `.py` and `.html`, so a relative path to `data/processed/` will not exist for a grader who runs the `.py` alone. Follow the M1 approach: **embed the merged hourly table** (≈ 8,784 rows × ~15 columns; a few hundred KB compressed, base64) in the notebook, and show in a cell how it was produced (`src/pipeline.py --grain hourly` → merge) and a checksum against `data/processed/hourly_bike_weather_2024.csv`. Never make the grader download and process tens of millions of rides during HTML rendering.

## 12. Risks, mitigations and open validation items

| Risk | Impact | Mitigation / decision rule |
|---|---|---|
| 2024 ZIPs (8+ GB) not on disk; download + 44 M-row pass may not finish in time | No hourly bike data → Q1–Q3 cannot be answered at hourly grain | Start the download first; develop on one month while it runs; never reverse-engineer hourly shares from daily totals |
| Weather source choice (station vs. reanalysis) | Smoothed rain weakens the rain effect; station gaps reduce N | Fetch both, apply the §6.2 decision rule, report the comparison; compare daily aggregates (LST window) with M1's NOAA daily data |
| Provider hourly precipitation time convention | One-hour misalignment between rain and rides | Open-Meteo = preceding-hour sum → shift by one hour (§6.2); confirm in docs at fetch time; spot-check a storm |
| Reanalysis drizzle hours | Too many hours classed "wet", diluting the rain effect | `≥ 0.2 mm` primary threshold with `> 0` sensitivity |
| Ambiguous NYC fall-DST hour with naive trip timestamps | Fake doubled hour + fake empty hour if zero-filled | Both ambiguous hours set to NaN, combined count in audit (§6.1) |
| Missing `scipy`/`statsmodels` in sandbox export | Export fails or cells error | Add to requirements and notebook script metadata; open the HTML |
| Weather and rides have autocorrelation | Full-data p-values too optimistic | Show residual autocorrelation; interpret via effect size; re-test on the independent subset (§7.1) |
| Independent subset has few wet hours | Low power; wide CI | Report its N; use it to confirm direction/size, not as the main effect estimate |
| Sparse rain in some quarter/hour/weekday cells | Unstable estimates | Show cell Ns, simplify sparse contrasts and avoid unsupported claims |
| Overfitting the rubric with many tests | Multiple testing and weak narrative (rubric grades the answer, not the number of techniques) | One regression per question + subset check; Holm for the four quarter contrasts; other alternatives only if they are decision-log entries |
| HTML export completes despite broken cells | Submission appears complete but is invalid | Open HTML and inspect loading, Q1–Q3 results, tables, plots and summary |

## 13. Definition of done / submission checklist

- [x] Repo actual structure and access reviewed; documentation paths reconciled (v1.1).
- [ ] `scipy`, `statsmodels` added to `requirements.txt` and notebook sandbox metadata.
- [ ] 2024 ride ZIP coverage complete; source and processing provenance recorded.
- [ ] M1 cleaning preserved and made transparent, including cross-midnight versus negative duration and the 11-03 DST explanation.
- [ ] Exactly 8,784 **elapsed** hourly rows and unique UTC keys; DST checks pass; ambiguous hours NaN, not 0.
- [ ] Hourly weather source chosen by the §6.2 rule (LCD vs. Open-Meteo), with the comparison shown; units, timestamp semantics and hour alignment documented and validated.
- [ ] Every number in Result/Answer/Summary/Decision log is a live f-string from notebook output.
- [ ] Hourly data embedded in the notebook so the Canvas `.py` runs on its own.
- [ ] Data merge audits, weather coverage and daily-ride reconciliation pass or discrepancies explained.
- [ ] Within-quarter wet/dry comparisons are shown for all four calendar quarters.
- [ ] Q1, Q2 and Q3 each include method, assumptions, result statistic, p-value, effect size, N, answer and limitations.
- [ ] Consecutive-hour dependence is shown (residual autocorrelation), explained, and the main result re-tested on the independent subset.
- [ ] Revised (hourly) question wording given alongside the original, with the reason (§7.0).
- [ ] Each Answer says whether the effect is big enough to matter, in rides.
- [ ] All M1 feedback and studio decisions addressed, including what changed and why.
- [ ] Decision log has three full entries; at least one alternative is actually run and compared.
- [ ] ~200-word nontechnical English summary includes a supporting number for each question.
- [ ] Notebook uses required heading order and loads documented data reproducibly.
- [ ] `SI618_M2_Group_11.py` and `SI618_M2_Group_11.html` are generated; **HTML opened and visually checked**.
- [ ] One group member submits both files in Canvas **before 3:30 PM Nov 16**.

## 14. Grading alignment

| Rubric component | Points | Plan coverage |
|---|---:|---|
| November 11 meeting | 20 | §3, §8 (retrospective record; meeting already occurred) |
| Response to feedback | 20 | §3, §8 |
| Question 1 | 40 | §7 Q1 |
| Question 2 | 40 | §7 Q2 |
| Question 3 | 40 | §7 Q3 |
| Summary of findings | 20 | §8 |
| Decision log | 20 | §9 |
| **Total** | **200** | |

## 15. References

1. Official SI 618 M2 instructions: https://github.com/cteplovs/si618-fa2026-student/blob/main/project/milestone-2.md
2. Official decision log: https://github.com/cteplovs/si618-fa2026-student/blob/main/project/decision-log.md
3. Team repository: https://github.com/ryan138076-gif/nyc-citibike-weather-analysis
4. Citi Bike System Data: https://citibikenyc.com/system-data
5. NOAA Daily Summaries (M1): https://www.ncei.noaa.gov/access/services/data/v1
6. Open-Meteo Historical Weather API (M2 candidate): https://open-meteo.com/en/docs/historical-weather-api
7. NOAA Local Climatological Data (M2 candidate, hourly station observations): https://www.ncei.noaa.gov/products/land-based-station/local-climatological-data
8. M1 implementation artifacts in the repository: `src/pipeline.py`, `SI618_M1_Group_11.py`, `SI618_M1_Group_11.html`, `reports/feasibility-notes.md`.

---

**Development principle:** preserve M1's research continuity and cleaning integrity; use hourly observations responsibly; separate descriptive evidence from statistical inference; prioritize M2's three answers and reproducible HTML over adding methods for their own sake.
