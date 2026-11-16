# SI 618 Milestone 1 — Citi Bike × Weather Project Requirements Document

> **Version:** v1.0 · 2026-10-14  
> **Project:** NYC Citi Bike Ridership and Weather Analysis  
> **Current scope:** Milestone 1 (M1) only. Maintain a sustainable structure for a future GitHub portfolio, but **do not conduct hypothesis testing or modeling in M1**.  
> **Deadline:** 2026-10-14, at the end of Project Studio (subject to the course webpage).  
> **Execution approach:** Divide the work into three independent sessions. Each session must end with verifiable deliverables, and the next session depends on successful acceptance of the previous one.

## 0. Project Background and Objectives

Examine descriptive associations between **daily NYC Citi Bike ridership in 2024** and **precipitation, temperature, and weekday/weekend status**. Aggregate individual Citi Bike trip records by their start date and merge them with daily observations from NOAA's Central Park weather station on `date`. The result will be a tidy dataset at the daily level, with at least three visualizations supporting three research questions.

### Definition of Success

- Use at least two traceable datasets from different sources and explain the new analytical capabilities enabled by merging them.
- Use executable Python code to load, clean, aggregate, and merge data, audit missing values, and track row counts.
- Present **3 Research Questions**. Each must specify the question, actual column names in the merged table, the comparisons or patterns that would constitute an answer, and how to interpret an absence of an observed relationship.
- Produce **at least 3 plots** with titles, labeled axes, and interpretations grounded in real data.
- Complete **3 Decision Log entries**, each containing Decision / Alternative / Evidence / Consequence. For **at least 1 entry**, demonstrate the difference by actually running an alternative approach.
- Submit a **marimo `.py` notebook and its HTML export**; the HTML must correctly display the analytical results.

### Non-goals (Out of Scope for M1)

- Do not calculate p-values, perform significance tests, infer regression coefficients, or train machine-learning models.
- Do not build hourly real-time weather analyses, precise route-level geospatial matching, or complex visualization dashboards.
- Do not sacrifice course deliverables or reproducibility for GitHub aesthetics.

## 1. Research Design (Initial Scope, Frozen for Now)

| Dimension | Requirement |
|---|---|
| Study area | NYC Citi Bike (avoid including `JC-` Jersey City files) |
| Study period | **Target:** 2024-01-01 through 2024-12-31; first validate the pipeline using January–March 2024 |
| Unit of observation | One row = one calendar date (daily) |
| Bike data source | Citi Bike Trip Histories: <https://citibikenyc.com/system-data> |
| Weather data source | NOAA NCEI Daily Summaries, Central Park, station `USW00094728` |
| NOAA download parameters | `PRCP`, `TMAX`, `TMIN`, metric units; see README for a sample URL |
| Join key | New York local ride-start date extracted from `started_at` ↔ NOAA `DATE` |
| Primary outcome | `daily_rides`; retain `member_rides` and `casual_rides` for description and possible extensions |
| Weather variables | `prcp_mm`, `tmax_c`, `tmin_c`, `avg_temp_c=(tmax_c+tmin_c)/2` (a proxy for daily average temperature only) |
| Calendar variables | `date`, `is_weekend`, `month` |

### Three Research Questions

1. **RQ1 — How is daily precipitation associated with Citi Bike ridership?**  
   **Columns:** `prcp_mm`, `daily_rides`. **Approach:** Compare ridership distributions on days with no rain, light rain, and heavier rain, or examine the trend between precipitation and ride counts. If no association is apparent, the distributions should overlap substantially or show no consistent directional pattern. Define and justify the thresholds in the notebook.
2. **RQ2 — Is the relationship between temperature and daily ridership nonlinear?**  
   **Columns:** `avg_temp_c`, `daily_rides`. **Approach:** Examine a scatterplot and descriptive trend for curvature or a peak. If there is no apparent nonlinear pattern, the relationship may appear roughly linear or show no clear variation.
3. **RQ3 — Does the precipitation–ridership relationship differ between weekdays and weekends?**  
   **Columns:** `prcp_mm`, `daily_rides`, `is_weekend`. **Approach:** Use grouped scatterplots/trends or descriptive comparisons of rainy versus non-rainy days. If no difference is apparent, the two groups should display similar patterns.

> **Interpretation boundary:** Report correlations and descriptive observations only; do not claim that weather causes changes in demand. A single Central Park weather station does not capture actual conditions at every trip origin. System size, holidays, and seasonal factors may confound the patterns.

## 2. Existing Project Foundation and Actual Status

The current starter ZIP, `SI618_CitiBike_M1_starter.zip`, contains:

```text
nyc-citibike-weather-analysis/
├── src/pipeline.py
├── notebooks/SI618_M1_CitiBike.py
├── data/raw/citibike/
├── data/raw/weather/
├── data/processed/
├── reports/
├── README.md
├── requirements.txt
└── .gitignore
```

**Completed:** The pipeline and marimo notebook skeleton have been written and tested with a small **synthetic dataset**.  
**Not completed:** Real Citi Bike and NOAA data have not yet been successfully downloaded, inspected, and analyzed in the current working environment. Therefore, **do not invent row counts, match rates, or findings**.  
**Known issues:** The existing notebook places `Data manipulation` before `Data description`; this must be reordered to match course requirements. Cross-CSV/cross-chunk `ride_id` duplicate checking has not yet been implemented. HTML data paths and dependencies still need validation.

---

# Session 1 — Data Collection and Feasibility Validation (Data Feasibility)

**Objective:** Demonstrate that both real datasets can be loaded, provide sufficient date coverage, and share a defensible join key. Prepare reliable files and audit outputs for subsequent sessions.

### Inputs

- `src/pipeline.py` and dependency files from the starter repository.
- Official Citi Bike ZIP archives for January, February, and March 2024. A ZIP may contain multiple CSV files; **all must be read**.
- NOAA Central Park daily observations CSV for 2024 (preferably covering the full year for later expansion).

### Tasks

- [ ] Set up the environment and run `python -m pip install -r requirements.txt`.
- [ ] Check the official links; download Bike archives by month and the NOAA CSV; record actual access/download dates.
- [ ] Inspect the Bike file inventory and column names, including whether any ZIP contains multiple CSV files.
- [ ] Verify that `ride_id`, `started_at`, `ended_at`, and `member_casual` exist; check timestamp interpretation and assignment to local calendar dates.
- [ ] Verify NOAA `DATE`, `PRCP`, `TMAX`, and `TMIN`, units, missing-value/quality flags, and duplicate dates.
- [ ] Calculate monthly file/CSV counts, raw row counts, proportions of valid timestamps, date ranges, and missingness.
- [ ] First run `python src/pipeline.py --months 1 2 3 --download` (omit `--download` if the data have already been downloaded); save the logs.
- [ ] Confirm that loading, daily aggregation, and the weather merge all run successfully; investigate null values and unusually high/low daily ride counts.

### Deliverables

- Raw test-month files in `data/raw/citibike/` and `data/raw/weather/noaa_2024.csv` (large raw files may remain local).
- Reproducible download and source documentation (in `README.md` or separate source notes).
- Initial versions of `data/processed/daily_bike_weather_2024.csv`, `trip_cleaning_audit.csv`, and `merge_audit.csv`.
- Brief Feasibility Notes documenting fields, date coverage, actual errors, and unresolved issues.

### Acceptance Criteria / Gate 1

- [ ] Both sources are loaded from **real files**, and neither the notebook nor the script requires a private API key.
- [ ] Every CSV inside each Bike ZIP is processed without omission.
- [ ] The three data grains can be precisely explained: trip, weather-station-day, and merged-day.
- [ ] Actual counts of matched and unmatched dates are reported; merely stating “merge successful” is insufficient.
- [ ] If only January–March has been processed, the report must not claim full-year findings.

**Blocker handling:** If full-year data are too large, retain the January–March validation results and prioritize fixing the processing workflow. However, a complete answer to RQ2 on temperature nonlinearity and seasonal variation still targets the full year.

---

# Session 2 — Data Cleaning, Merging, and EDA (Data Engineering + Visualisation)

**Objective:** Produce the final tidy table, transparent cleaning audits, and three real-data visualizations aligned with the research questions, expanding to the full year wherever feasible.

### Inputs

- Real source files and audit outputs that passed Session 1 acceptance.
- Finalized column definitions for the research questions.

### Tasks

- [ ] Read large files monthly or in chunks, process all monthly CSV members, and expand to full-year 2024 where resources permit.
- [ ] Parse timestamps and filter invalid records, including unparseable timestamps and `ended_at <= started_at`; explicitly document the counting rules.
- [ ] Add, or clearly disclose the limitations of, **cross-chunk and cross-CSV `ride_id` deduplication audits**. Do not claim global deduplication if only within-chunk duplicates are checked.
- [ ] Aggregate `daily_rides`, `member_rides`, and `casual_rides` by the calendar date of `started_at`.
- [ ] Clean weather dates and numeric fields, confirm that `PRCP` is in millimeters and temperatures are in degrees Celsius, and distinguish zero precipitation from missing precipitation.
- [ ] Construct a calendar-date index and distinguish “no ride observations” from “confirmed zero rides”; do not fill missing values with zero without justification.
- [ ] Merge on `date` with one-to-one validation; preserve the merge indicator and matched/unmatched counts.
- [ ] Automatically report rows, columns, row grain, data types, units, and missingness for raw Bike data, weather data, and the final merged data.
- [ ] Produce three plots with observations grounded in actual data: (1) precipitation category vs. daily rides; (2) temperature vs. daily rides; (3) precipitation and demand, grouped by weekend status.
- [ ] Audit visualization-sample filtering: clearly state whether dates missing `daily_rides` or the relevant weather variable are excluded.

### Deliverables

- Updated `src/pipeline.py`.
- Validated `data/processed/daily_bike_weather_2024.csv` and audit files.
- Data-description tables and at least **3 plots based on real data** in the notebook.
- One or two objective interpretation sentences per figure (not placeholder text).

### Acceptance Criteria / Gate 2

- [ ] Each row uniquely represents one `date`; there are no unintended one-to-many joins.
- [ ] Total row counts before and after cleaning, including losses at each step, can be traced through executed code.
- [ ] The actual observation period is recorded, and reasons for unmatched dates can be explained.
- [ ] Every column required by the three research questions appears in the final merged dataset.
- [ ] All three figures have titles, axes labeled with units, and interpretations, with a one-to-one correspondence to the research questions.
- [ ] No statistical significance tests or model training are performed.

---

# Session 3 — Writing, Decision Evidence, Marimo, and Submission (M1 Delivery)

**Objective:** Organize real results into the instructor-required marimo notebook, complete the Decision Log, validate the HTML export, and prepare for Canvas submission and later GitHub reuse.

### Required Notebook Section Order

1. `Title and group`
2. `Overview`
3. `Research questions`
4. `Data sources`
5. `Data description`
6. `Data manipulation`
7. `Data visualisation`
8. `Decision log`

> **Required fix:** The current starter places `Data description` and `Data manipulation` in an order that conflicts with course requirements. Correct their order.

### Tasks

- [ ] Add every group member’s name and uniqname; explain the additional research value made possible by merging the datasets.
- [ ] For each of the three Research Questions, provide the relevant column names, observable answer criteria, and what the absence of a relationship would look like.
- [ ] For each dataset, document the publisher, URL, actual download date, and license/terms of use; justify the merge columns.
- [ ] **Generate data-description tables through notebook code**, including pre- and post-merge rows/columns, data grain, variable types, units, and missing rates.
- [ ] Add short Markdown explanations for each cleaning, aggregation, and merge step in Data manipulation; display row counts retained and lost.
- [ ] Complete the interpretations of all three plots without making causal claims.
- [ ] Write **3 Decision Log entries**, each with Decision / Alternative / Evidence / Consequence.
- [ ] For at least one decision, **actually execute an alternative approach** and calculate/present a numerical, tabular, or visual comparison with the chosen approach.
- [ ] Avoid “decorative decisions” with no measurable impact; favor real choices about cleaning, missing data, joins, or deduplication.
- [ ] Follow the course naming convention and use the **actual group name** in `SI618_M1_<group name>.py`.
- [ ] Export HTML and inspect the rendered page, not merely the command’s exit code; confirm figures, tables, and dynamic values are present rather than tracebacks or blank outputs.
- [ ] In the GitHub README, document how to obtain the data, reproduce the workflow, comply with terms of use, and understand known limitations; large datasets need not be uploaded to the repository.

### Export Command (Replace the Placeholder with the Actual Group Name)

```bash
uvx marimo export html --sandbox SI618_M1_<group name>.py -o SI618_M1_<group name>.html
```

If the file is in `notebooks/`, the corresponding relative path may be supplied, but the submitted filename must follow the instructor’s convention. Ensure the data and dependencies are accessible during HTML export.

### Deliverables

- `SI618_M1_<group name>.py`: complete marimo notebook.
- `SI618_M1_<group name>.html`: an export that opens correctly and fully displays the actual results.
- Complete README, processing scripts, and audit files for team/GitHub maintenance; only the two files above are required for course submission.

### Acceptance Criteria / Gate 3

- [ ] The notebook runs and follows the instructor’s required section order.
- [ ] Data sources, types, units, missing values, and match counts are supported by **real data**.
- [ ] At least 3 Research Questions, at least 3 plots, and 3 complete Decision Log entries are included.
- [ ] At least 1 Decision Log consequence is supported by **results from an executed alternative analysis**.
- [ ] The HTML file has been opened and manually checked, with no cascading errors caused by missing data.
- [ ] The group submits only the `.py` and `.html` files to Canvas.

---

## 3. Rubric Mapping and Priorities

| Section | Points | Project-Specific Acceptance Focus |
|---|---:|---|
| Overview | 10 | Explain the value of combining Bike and Weather data |
| Research questions | 10 | 3 RQs, column names, observable answers, and null/no-effect scenarios |
| Data sources | 20 | Publisher, URL, download date, terms, and justification for date matching |
| Data description | 40 | Code-computed pre-/post-merge row and column counts, grain, types, units, and missingness |
| Data manipulation | 50 | Executable workflow with row-count changes at every step and matched/unmatched counts |
| Data visualisation | 50 | 3+ plots with complete labels, clear interpretations, and alignment to RQs |
| Decision log | 20 | Three complete entries, including at least one experimentally tested alternative |
| **Total** | **200** | Prioritize the 140 points associated with data description, manipulation, and visualization |

## 4. Risk Register and Mitigation Principles

| Risk | Impact | Mitigation Principle |
|---|---|---|
| Downloading/processing large annual Citi Bike files and memory pressure | Long processing times and out-of-memory errors | Read monthly ZIP archives and CSV chunks; aggregate to daily granularity as early as possible |
| Inadequate date coverage | Weakens RQ2 and full-year conclusions | Report actual temporal coverage; prioritize expansion to all of 2024 |
| Duplicate `ride_id` values | Possible double-counting in `daily_rides` | Add cross-chunk/file audits and report the cleaning rule |
| Missing weather-station observations | Biased samples in precipitation/temperature plots | Display unmatched counts and missingness; do not replace NA with zero |
| NOAA quality flags or units | Unreliable weather values | Validate official field definitions, units, and quality flags |
| Weather confounded with operational factors | Risk of misinterpreting correlation as causation | Limit claims to descriptive relationships and acknowledge seasonal/system-size factors |
| HTML export cannot access external file paths | Export may appear successful but render blank or show errors | Use stable paths and manually inspect the final HTML |
| Reusing course data and applicable terms | Incomplete source disclosure | Clearly identify publishers, terms, and download dates in README and notebook |

## 5. Session Handoff Template

At the end of each session, complete the following template so the next session can continue:

```markdown
### Session [1/2/3] Handoff
- Completed tasks:
- Files created/modified:
- Actual data row counts and date range:
- Data-quality issues discovered:
- Unresolved blockers:
- Top priority for the next session:
- Locations of evidence files/screenshots/logs:
```

## 6. Official References and Working Files

- SI618 [Milestone 1](https://github.com/cteplovs/si618-fa2026-student/blob/main/project/milestone-1.md)
- SI618 [Decision Log](https://github.com/cteplovs/si618-fa2026-student/blob/main/project/decision-log.md)
- [Citi Bike System Data](https://citibikenyc.com/system-data)
- [NOAA NCEI Daily Summaries](https://www.ncei.noaa.gov/access/services/data/v1)
- Current project starter: `SI618_CitiBike_M1_starter.zip` (not a fully validated M1 submission)

> **Factual status statement:** This document sets out implementation requirements based on the reviewed course instructions, agreed research design, and status of the starter code. All real-data statistics, plot findings, matched/unmatched counts, and evidence from alternative analyses must be filled in from actual outputs after completing the three sessions; none should be predetermined.
