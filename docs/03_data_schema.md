# Phase 3 — Data Pipeline & Weekly e1RM Construction

## Objective
Transform raw workout logs into a clean, analysis-ready weekly strength dataset.

This phase establishes a reproducible pipeline from raw inputs to a modeled performance metric, ensuring correctness before forecasting.

---

## Raw Data Source
- Source: Strong app export (CSV)
- Location: `data/raw/strong_sets_initial.csv`
- Granularity: one row per completed set
- Key fields (required):
  - date
  - exercise
  - weight_kg
  - reps
  - set_number
  - session_name

Raw data is treated as immutable input.

---

## Ingestion & Validation
A Python ingestion script loads the CSV into SQLite with:
- Schema validation (required columns enforced)
- Type coercion:
  - `date` → stored as `YYYY-MM-DD` text (SQLite-friendly)
  - `weight_kg` → numeric
  - `reps`, `set_number` → integers
- String normalization:
  - `exercise`, `session_name` trimmed with `str.strip()`
- Filtering to core lifts (for forecasting scope):
  - Bench Press
  - Squat
  - Deadlift

Design principle: fail fast with clear errors if the input format changes.

---

## Database Layer
Validated data is stored in:
- Database: `data/training.sqlite`
- Table: `sets`
- Row meaning: one row = one set performed

SQLite is used to:
- enforce structure
- support reproducible querying
- cleanly separate raw inputs from derived outputs

---

## e1RM Definition (Epley)
For each set we compute estimated 1RM (e1RM) using Epley:

e1RM = weight_kg × (1 + reps / 30)

This standardizes strength estimates across sets performed at different rep counts.

---

## Weekly Aggregation Logic
We define weekly performance as:

> Weekly max e1RM per lift (Mon–Sun week)

Steps:
1. Map each `date` to `week_start` (Monday of that week)
2. Compute `e1rm` for every set
3. Group by (`week_start`, `exercise`)
4. Take the maximum e1RM within each group

Rationale:
- Weekly max represents best strength expression that week
- It is intentionally “noisy but honest”; smoothing is handled in later phases

---

## Output Table
The derived dataset is stored as:
- Table: `weekly_e1rm`
- Columns:
  - week_start
  - exercise
  - e1rm

This table becomes the primary modeling input for forecasting.

---

## Limitations
- Early weeks have sparse history; trend inference is weak initially
- Weekly max e1RM is volatile at short horizons
- No fatigue/deload/injury modeling at this phase (added later)
