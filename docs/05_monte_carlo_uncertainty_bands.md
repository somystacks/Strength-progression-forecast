# Phase 5 — Monte Carlo Uncertainty Bands

## Objective
Convert deterministic scenario forecasts into probabilistic forecasts by generating uncertainty bands for weekly max e1RM (p10 / p50 / p90 and p5 / p95) across the forecast horizon.

The goal is not to predict a single outcome, but to bound plausible outcomes under uncertainty.

---

## Inputs
- Source dataset: `weekly_e1rm` (weekly max e1RM per lift; Mon–Sun week)
- Starting point: last observed weekly max e1RM per lift
- Baseline weekly gains (Δ₀) per lift (explicit assumptions)
- Adherence scenarios:
  - 100% (multiplier 1.0)
  - 75% (multiplier 0.7)
  - 50% (multiplier 0.45)
- Volatility estimate (σ): estimated from historical week-to-week e1RM differences (`diff_sigma`)
  - Note: early phases have limited history; σ is conservative and will be recalibrated quarterly

---

## Deterministic Model Recap
Weekly expected gain decays over time (diminishing returns):

Δₜ = Δ₀ / log(1 + t + k)

Scenario adherence scales weekly gain:

Δₜ(scenario) = Δₜ × adherence_multiplier

This produces smooth, monotonic-but-flattening trajectories per lift and scenario.

---

## Monte Carlo Simulation
We simulate many plausible futures using:

e[t+1] = e[t] + expected_gain[t] + noise[t]

Where:
- expected_gain[t] comes from the diminishing returns model scaled by scenario adherence
- noise[t] ~ Normal(0, σ) is a weekly stochastic term representing biological and measurement variability

For each (lift, scenario), multiple simulation runs are generated and summarized as percentile bands:
- Central path: p50 (median)
- 80% band: p10–p90
- 90% band: p5–p95

---

## Outputs
### 1) Visualizations
For each lift, plot:
- Median paths for 100% / 75% / 50%
- Shaded uncertainty bands (p10–p90 and p5–p95)

### 2) Tables
We produce weekly tables per lift/scenario with:
- week_start
- p10, p50, p90 (and optionally p5/p95)

### 3) Persisted Forecast Table (SQLite)
Forecast bands are saved to SQLite:

- Database: `data/training.sqlite`
- Table: `forecast_bands`
- Primary key: (week_idx, exercise, scenario)

Row count sanity check:
- 44 weeks × 3 lifts × 3 scenarios = 396 rows

---

## Companion Tables (Per-Lift)

For each lift, we provide a week-by-week table aligned with the corresponding forecast plot.
Each table reports percentile bands that bound plausible outcomes:

- **p50**: median (central expectation)
- **p10–p90**: 80% uncertainty band
- (Optionally p5–p95 for wider bounds)

These tables are intended for inspection, review, and decision support, not point prediction.

### Bench Press — Weekly Forecast Bands
Columns: week_start | p10 | p50 | p90

### Squat — Weekly Forecast Bands
Columns: week_start | p10 | p50 | p90

### Deadlift — Weekly Forecast Bands
Columns: week_start | p10 | p50 | p90

Note: Tables are generated directly from the persisted `forecast_bands` SQLite table to ensure consistency with plotted results.

Example (Deadlift, 100% adherence — first 6 weeks):

| week_start | p10 | p50 | p90 |
|-----------|-----|-----|-----|
| 2026-02-09 | … | … | … |
| 2026-02-16 | … | … | … |
| 2026-02-23 | … | … | … |
| 2026-03-02 | … | … | … |
| 2026-03-09 | … | … | … |
| 2026-03-16 | … | … | … |


---

## Interpretation Guidance
- Forecasts are distributions, not point predictions
- Bands widen with horizon because weekly uncertainty accumulates over time
- Early overlap across scenarios is expected and honest; separation increases as adherence compounds

---

## Limitations
- Only two weeks of historical data currently; σ is weakly estimated
- Weekly noise is modeled as independent normal noise (no fatigue autocorrelation yet)
- No explicit injury/deload/stress event modeling in this phase

---

## Next Phase
Phase 6 will introduce decision rules and recalibration:
- Alert thresholds using percentile bands (e.g., repeated underperformance below p10)
- Quarterly re-estimation of Δ₀ and σ using accumulated training history
- Optional upgrades: autocorrelated noise, deload logic, and lift-specific seasonality
