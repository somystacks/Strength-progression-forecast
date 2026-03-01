# Phase 7 — Backtesting Plan (Scaffold)

## Objective
Evaluate forecast accuracy and calibration over time using rolling forecast origins.

## Why backtesting needs forecast origins
A backtest is not a single comparison. It requires multiple forecasts made at different points in time (forecast origins) and comparing them to later actual outcomes.

Example:
- Forecast generated on 2026-02-02 predicting weeks 2026-02-09, 2026-02-16, ...
- Forecast generated on 2026-02-09 predicting weeks 2026-02-16, 2026-02-23, ...
- etc.

## Proposed schema change (future)
Persist forecasts with origin + target:
- forecast_origin_week_start
- target_week_start
- exercise
- scenario
- p10/p50/p90/p5/p95

This allows:
- point-in-time reproducibility
- proper historical evaluation
- comparing how recalibration changes forecast quality

## Metrics to compute (once >= 8–12 weeks of data)
- MAE / RMSE: |actual - p50|
- Bias: mean(actual - p50)
- Coverage: % of actuals that fall within p10–p90 (should be ~80%)
- Scenario selection performance: compare 100/75/50% baselines

## When to run
- First meaningful backtest: after 8+ weeks
- Recalibration cycle: every 8–12 weeks (quarterly)