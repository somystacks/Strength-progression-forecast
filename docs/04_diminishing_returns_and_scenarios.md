# Phase 5 — Diminishing Returns & Scenario Forecasting

## Objective
Model plausible future weekly strength trajectories (e1RM) under different adherence scenarios, while explicitly accounting for diminishing returns and uncertainty.

This phase does not aim to predict a single outcome, but to bound realistic outcomes given known and unknown factors.

---

## Modeling Philosophy
- Strength gains exhibit diminishing returns over time
- Adherence affects the *rate* of improvement, not peak potential
- Forecast uncertainty increases with time
- Weekly e1RM is modeled as the primary state variable

---

## Baseline Assumptions
- Starting point: last observed weekly max e1RM per lift
- Baseline early-phase weekly gains (kg/week):
  - Bench Press: 0.4
  - Squat: 0.6
  - Deadlift: 0.9
- Gains decay over time using a logarithmic diminishing-returns function

---

## Diminishing Returns Model
Weekly expected gain is defined as:

Δₜ = Δ₀ / log(1 + t + k)

Where:
- Δ₀ is the baseline weekly gain
- t is weeks since forecast start
- k controls the rate of decay

This formulation models *process-level* weekly adaptation rather than cumulative closed-form growth.

---

## Adherence Scenarios
Adherence modifies weekly gain multiplicatively:

| Scenario | Multiplier | Interpretation |
|:-------|:----------:|:---------------|
| 100% | 1.0 | Full program adherence |
| 75% | 0.7 | Occasional missed sessions |
| 50% | 0.45 | Inconsistent training |

---

## Deterministic Scenario Outputs
For each lift and scenario:
- Weekly e1RM trajectories are generated
- Growth is monotonic but flattening
- Scenario gaps widen over time due to compounding effects

These outputs represent *expected paths*, not guaranteed outcomes.

---

## Uncertainty Estimation (Pre-Monte Carlo)
Weekly volatility (σ) is estimated from historical week-to-week differences in e1RM:

- σ captures biological variability and measurement noise
- Due to limited data, σ is conservative and transparent
- NaN estimates are defaulted to 1.0 kg

At this stage, σ is prepared but not yet injected stochastically.

---

## Limitations
- Only two weeks of observed data
- No injury, deload, or fatigue modeling yet
- Deterministic paths do not yet reflect probabilistic outcomes

---

## Next Phase
Phase 6 will introduce Monte Carlo simulation:
- Randomized weekly gains around the expected trajectory
- Forecast bands (e.g. 80%, 95%)
- Decision thresholds for reassessment and deloading
