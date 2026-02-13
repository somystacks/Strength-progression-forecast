Problem Statement: Strength Progression Forecasting Model
Phase 1 Foundation — February to December 2026
1. Primary Objective
Forecast weekly estimated 1RM for core compound lifts (deadlift, squat, bench press) from February 2026 through December 31, 2026, based on a structured 4x/week resistance training program. The model will generate progression trajectories under defined adherence scenarios to set data-driven expectations for achievable strength outcomes.
Why this target?
1RM is an observable, quantifiable metric that directly reflects program efficacy. Program quality itself will be evaluated post hoc by comparing actual vs. projected 1RM trajectories—not predicted directly.
2. Scope & Inputs
Category
Representation
Notes
Baseline state
Current 1RMs (e.g., deadlift 220kg @ 95kg BW), training age (~4 years), bodyweight
Fixed initial conditions
Program structure
Weekly volume (sets × reps × load), exercise selection, progression rules (e.g., +2.5kg/week on deadlift)
Deterministic input schedule
Adherence behavior
Binary session completion flag (attended/missed); modeled scenarios: 100%, 75%, 50% adherence
Primary sensitivity variable
Recovery capacity
Treated as fixed qualitative prior (consistent 5am routine, stable sleep/nutrition)
Not dynamically modeled in Phase 1
Constraints
Family commitments, travel windows
Modeled as scheduled adherence reductions
Transparency note: Abstract inputs (training age, recovery capacity) are represented as fixed priors in Phase 1—not dynamically modeled variables—to avoid over-engineering before validating core signal.
3. Analytical Approach (Phased Sequence)
Phase 1: Deterministic baseline
Linear regression on weekly programmed load increases
Simple exponential smoothing for short-term trend continuity
Phase 2: Biological realism
Apply diminishing returns curve (logarithmic decay on weekly % gains) based on proximity to strength standards for 95kg intermediate lifters
Anchor progression rates to evidence-based benchmarks (e.g., Phraks intermediate progression tables)
Phase 3: Uncertainty & scenarios
Monte Carlo simulation to generate confidence intervals (±1σ, ±2σ) around deterministic trajectory
Scenario analysis: overlay adherence variations (100% vs. 75% vs. 50%) to quantify consistency impact
External validation deferred to Phase 4: Benchmark final projection against population norms only after model calibration
Why this sequence? Restraint first—prove signal exists before layering complexity.
4. Deliverables
Core output: Weekly projected 1RM table (Feb–Dec 2026) with 80% confidence intervals
Scenario dashboard: Side-by-side trajectories for 100%/75%/50% adherence paths
Deviation alert framework: Thresholds for when actual performance warrants program adjustment (e.g., >2σ deviation for 3 consecutive weeks = deload trigger)
Alignment assessment: Post-hoc comparison of projected trajectory against evidence-based progression ranges for intermediate lifters (95kg male, 4x/week frequency)
Note: "Alignment assessment" replaces subjective "validation score"—focusing on factual comparison rather than verdict declaration.
5. Value Proposition
Personal: Replace hope-based expectations with quantified milestones; visualize the cost of inconsistency via scenario comparison
Generalizability: Model outputs are scoped to lifters matching key priors (95±5kg male, intermediate training age, 4x/week availability). Explicitly not generalizable beyond this demographic without recalibration.
6. Key Assumptions & Limitations
Nutrition, sleep quality, and life stressors remain stable relative to baseline
No acute injuries or major physiological disruptions occur
Diminishing returns accelerate as proximity to genetic potential increases (logarithmic decay)
Data sparsity: Limited historical adherence data in early phases increases uncertainty; favors simpler models initially
Model accuracy degrades beyond 12 weeks; requires quarterly recalibration using actual performance data