# Phase 6 — Decision Rules and Recalibration

## Objective
Convert probabilistic weekly e1RM forecasts into an operational monitoring system that:
- compares actual weekly performance against forecast uncertainty bands, and
- triggers simple, defensible coaching actions (alerts) when performance persistently deviates.

This phase is designed as a decision-support layer, not a training plan generator.

---

## Baseline scenario used (75%)
All monitoring comparisons use the **75% adherence** scenario by default.

Rationale:
- It is the most realistic baseline for real-world training consistency.
- It avoids optimistic bias that would over-trigger “underperformance” alerts.

Note: The baseline scenario can be changed later (e.g., use 100% during a focused block or 50% during high-disruption periods).

---

## Rule definitions (alerts)
Alerts are computed per lift (Bench Press, Squat, Deadlift) using actual weekly max e1RM vs the forecast bands:

- **OK**
  - Actual performance is within normal variation or there is insufficient streak evidence.

- **YELLOW: underperforming (2w below p10)**
  - Triggered when actual e1RM is **below p10** for **2 consecutive evaluated weeks**.
  - Interpretation: likely fatigue, poor recovery, or execution inconsistency. Investigate sleep/nutrition/stress and review programming.

- **RED: deload trigger (3w below p10)**
  - Triggered when actual e1RM is **below p10** for **3 consecutive evaluated weeks**.
  - Interpretation: persistent underperformance beyond expected variance. Deload/reduce fatigue and reassess volume/intensity.

- **BLUE: recalibrate gains upward (3w above p90)**
  - Triggered when actual e1RM is **above p90** for **3 consecutive evaluated weeks**.
  - Interpretation: baseline gains are too conservative (or training response improved). Re-estimate parameters (Δ₀ and σ).

---

## How streaks are computed
Streaks are computed separately for each exercise and are based on consecutive `True` values in boolean flags:

- `below_p10 = actual_e1rm < p10`
- `above_p90 = actual_e1rm > p90`

For each lift, rows are sorted by `week_start`, and a running counter resets to 0 whenever the flag is `False`.

This produces:
- `below_p10_streak`
- `above_p90_streak`

Alerts are then assigned using the threshold logic described above.

---

## Output tables (SQLite)
Alerts are persisted to SQLite for reproducibility and future automation.

- Database: `data/training.sqlite`
- Tables used:
  - `weekly_e1rm` (actual weekly max e1RM by lift)
  - `forecast_bands` (p5/p10/p50/p90/p95 by week, lift, scenario)
  - `alerts` (merged view + flags + streaks + final alert)

The evaluation dataset is restricted to weeks where forecasts exist (i.e., `week_start >= forecast_start`), so earlier historical weeks that predate the forecast origin are excluded from evaluation by design.

A `forecast_origin` field is stored with alerts to record the forecast start used for monitoring.

---

## Limitations and recalibration cadence
- **Limited early data:** With only a few weeks of history, σ (weekly volatility) is weakly estimated and uncertainty bands may be miscalibrated.
- **No fatigue autocorrelation:** Weekly noise is treated as independent (no explicit fatigue carryover yet).
- **Scenario simplification:** The 75% scenario is a heuristic proxy for adherence, not a measured adherence model.

Recalibration plan:
- **Quarterly (every 8–12 weeks):**
  - re-estimate baseline gains (Δ₀) per lift using observed week-to-week trends
  - re-estimate σ from the growing history of weekly changes/residuals
  - regenerate `forecast_bands` and continue monitoring