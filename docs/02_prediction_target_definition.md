# Prediction Target Definition — Weekly Estimated 1RM

## 1. Target (what we predict)
For each lift (squat, bench press, deadlift), the model predicts a single
weekly estimated one-repetition maximum (e1RM) value for each calendar week
(Monday–Sunday).

This value represents the best expression of strength capacity achieved
during that week.

---

## 2. Source of truth (which sets count)
For each lift in a given week, weekly strength is represented by:

- [x] The set with the highest estimated 1RM (by formula)
- [ ] The single heaviest successful working set (by load)
- [ ] The top set only (if plan marks a “top set”)
- [ ] Other

Definition of a “successful” set:
- [x] Completed prescribed reps without assistance or failed reps
- [ ] Completed reps regardless of form notes
- [ ] Other

Operational rule:
All successful sets for a lift within a week are converted to estimated 1RM
values using a consistent formula. The maximum estimated 1RM observed in that
week is selected as the weekly strength value for that lift.

---

## 3. e1RM formula (consistent across the project)
Estimated one-repetition maximum (e1RM) is calculated using the Epley formula:

e1RM = weight × (1 + reps / 30)

This formula is applied consistently across all lifts, weeks, and scenarios
to ensure comparability of weekly strength estimates over time.

---

## 4. Weekly aggregation (when multiple sessions exist)
If a lift occurs multiple times within the same calendar week (Monday–Sunday),
weekly e1RM is defined as:

Weekly e1RM(lift, week) = max(e1RM of all successful sets for that lift in that week)

This definition aligns with the project’s goal of tracking the best expression
of weekly strength capacity for each lift.

---

## 5. Missing data rules
(To be defined)

---

## 6. Adherence definition (for scenarios)
(To be defined)

---

## 7. Notes / edge cases
(To be defined)

