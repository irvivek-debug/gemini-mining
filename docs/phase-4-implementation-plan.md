# Phase 4 — Implementation Plan: Data Realism Workstream

**Scope of this plan:** the data build only. Agent implementation is a second plan, written after the data lands, because per the Phase 5 ordering constraint agents come last and building them against unrealistic data bakes the flaw into all 100.

> **GATE.** This is the last gate before code. Approve before implementation begins.

---

## 0. Why this plan is bigger than Phase 3 §2 said

Phase 3 proposed seven additive injections and promised "no existing row is altered." Probing the data further shows that promise cannot survive the requirement that it look real. Four independent tests, all failed:

| Test | Expected in real data | Measured | Verdict |
|---|---|---|---|
| Lag-1 autocorrelation, `telemetry_stream` | **0.7 – 0.95** (rotating equipment, hourly) | **0.003 – 0.035**, one negative | White noise. Not a physical process. |
| Diurnal / shift structure, vibration | visible 12-h shift cycle | hour-of-day means 4.92 – 5.17, flat | No operating rhythm. |
| Recovery vs feed & tailings grade | near-deterministic — recovery is *defined* by mass balance | **corr 0.058 / 0.065** | Physically impossible. |
| Repair cost vs actual duration | 0.7 – 0.9 (labour is most of cost) | **corr 0.017** | A 12-hour repair costs the same as a 1-hour one. |

`biometric_fatigue_logs` is the one partial success: `sleep_deficit` ↔ `microsleep` = 0.466 and ↔ `alert` = 0.526, which someone genuinely modelled. But `sleep_deficit` ↔ `heart_rate_bpm` = **−0.116** — the wrong sign. Sleep deprivation raises resting heart rate.

**The conclusion that drives this plan:** appending realistic data to unrealistic history produces a visible seam and leaves the underlying tells in place. The metallurgy failure is the most exposed — the two-product recovery formula is the first thing a metallurgist checks, and it takes ten seconds.

**Therefore the approach changes from *append* to *regenerate, with originals preserved*.** Every original table is copied to `<name>_original_20260810` before being rewritten. Nothing is destroyed; everything is reversible.

---

## Global constraints

- **Python 3.12** (`python3`). System Python is 3.9 and cannot run the Cloud SDK path.
- **Every generated series must pass the realism suite in Task 9.** A task that loads data failing those assertions is not done.
- **No table is dropped.** Rewrites are `CREATE OR REPLACE` only after the `_original_` copy exists and is row-count verified.
- **Schemas are never changed.** Same columns, same types, same partitioning and clustering. Only values change. This keeps the four property graphs and the seven BQML models valid.
- **Deterministic seed** (`SEED = 20260810`) so any reviewer regenerates byte-identical data.
- **No hardcoded model IDs** anywhere. No service-account keys. No string-interpolated SQL.
- Timezone: all timestamps UTC, matching existing rows.
- **Sampling grids preserved exactly** (verified against the live tables, not assumed):
  | Table | Grid | Points | Window (UTC) |
  |---|---|---|---|
  | `telemetry_stream` | **2-hourly** | 2004 timestamps | `2026-01-01 00:00` → `2026-06-16 22:00` |
  | `metallurgical_recovery`, `crusher_states` | daily | 167 | `2026-01-01` → `2026-06-16` |
  | `biometric_fatigue_logs`, `fatigue_logs_node` | daily × 20 operators | 167 × 20 = 3340 | `2026-01-01` → `2026-06-16` |
- **Calibration targets come from `data/profile/stats.json`**, a profile of the live tables captured before any rewrite. Generators read it; no statistic is hardcoded from memory.
- **Generated series must reconcile with `assets.current_state`**, the JSON snapshot of each asset's present reading. This is a free consistency check the original data fails, and it fixes the end-point of every ramp.

---

## Task 1: Generator scaffold, config, and reversible backups

* **Files**: create `data/generator/config.py`, `data/generator/common.py`, `data/generator/backup.py`, `data/requirements.txt`
* **Depends on**: none
* **Already in place**: `data/profile/schemas.json` (all 28 table schemas with partitioning and clustering) and `data/profile/stats.json` (calibration statistics), both captured from the live dataset before any rewrite. `config.py` loads these rather than restating their numbers.
* **Deliverable**: a seeded RNG, the shared stochastic primitives every later task uses, and a verified backup of all tables being rewritten.
  * `ou_process(n, mu, sigma, phi, seed)` — Ornstein-Uhlenbeck / AR(1): `x[t] = mu + phi*(x[t-1]-mu) + eps`. This single function is what fixes the autocorrelation failure.
  * `diurnal(ts, amplitude, peak_hour)` — 24-h sinusoid for shift rhythm.
  * `shift_step(ts)` — 12-h day/night step (06:00 / 18:00 handover).
  * `weekly_dip(ts, magnitude)` — planned maintenance window.
  * `dropout_mask(n, rate)` — sensor outages; rows omitted, not zeroed.
  * `stuck_sensor(series, rate, run_len)` — flatline runs, a real and commonly-seen fault.
* **Verification**:
  ```
  py312 -m pytest data/generator/tests/test_common.py -v
  ```
  Expected: `ou_process` with `phi=0.85` yields measured lag-1 autocorrelation in `[0.80, 0.90]` over n=4000; `dropout_mask` yields rate within ±0.1pp; PASS on all.
  ```
  bq query 'SELECT COUNT(*) FROM mining_data.telemetry_stream_original_20260810'
  ```
  Expected: `10020`, matching the live table exactly.

---

## Task 2: Telemetry generator — physics, rhythm, and degradation

* **Files**: create `data/generator/telemetry.py`, `data/generator/tests/test_telemetry.py`
* **Depends on**: Task 1
* **Deliverable**: a full rewrite of `telemetry_stream` — same schema, same 2-hourly grid, **13 asset·metric series × 2004 points ≈ 26,000 rows** (up from 5 series / 10,020 rows).

  **Per-asset metric model.** Each series is `OU(phi=0.85–0.92) + diurnal + shift_step + weekly_dip`, calibrated so the mean and standard deviation match the *existing* table's values. The distribution is preserved; only its temporal structure is repaired. Anyone comparing summary statistics before and after sees no change — which is the point.

  | Asset | Metrics | Notes |
  |---|---|---|
  | PUMP-104A | `vibration_hz`, `temperature_c` | temperature **lags vibration by 3 h** (thermal mass); degradation ramp applied |
  | CRUSHER-03 | `feed_rate_tph`, `rotational_torque_nm` | torque responds to feed rate with correlation ≈ 0.75 — a crusher working harder on more feed |
  | MILL-01 | `power_draw_mw`, **`temperature_c`, `rotational_speed_rpm` (new)** | closes gap A3; reconciles `assets.current_state` |
  | CONVEYOR-02 | **`belt_tension_kn`, `speed_mps`, `load_pct` (new)** | closes gap A2 |
  | TRUCK-08 | **`engine_temp_c`, `payload_tons`, `speed_kmh` (new)** | closes gap A2 |

  **Degradation ramp (A1).** PUMP-104A bearing wear over the final 21 days, applied as an exponential envelope on top of the OU process, not a linear add: `vibration *= 1 + k*exp(alpha*(t-t0))`. The end-point is **not chosen freely — it is fixed by `assets.current_state`**, which records PUMP-104A at `vibration_hz 12.5`, `temperature_c 85.2`. The ramp terminates there, so the time series and the asset snapshot finally agree. `temperature_c` follows with the 3-h lag. Harmonic content is out of scope at 2-hourly sampling and is not faked.

  **Every new series lands on its `assets.current_state` value** at the final timestamp: MILL-01 `temperature_c 88.5` / `rotational_speed_rpm 14.8`; CONVEYOR-02 `speed_mps 4.5` / `belt_tension_kn 25.4` / `load_pct 88.0`; TRUCK-08 `speed_kmh 32.5` / `payload_tons 218.4` / `engine_temp_c 92.1`.

  **Cross-table consistency.** `CRUSHER-03.feed_rate_tph` appears in *both* `telemetry_stream` (2-hourly) and `crusher_states` (daily). Today they are independent draws. After this task the daily series is the daily mean of the 2-hourly one — an inconsistency a reviewer can check in one join.

  **Faults.** 0.4% dropout; two stuck-sensor runs of 6–10 h on non-critical metrics.
* **Verification**:
  ```
  py312 -m pytest data/generator/tests/test_telemetry.py -v
  ```
  Expected, all PASS:
  - lag-1 autocorrelation per asset·metric ∈ `[0.75, 0.95]`
  - hour-of-day means show amplitude > 3% of series mean (diurnal present)
  - PUMP-104A `vibration_hz` mean over the final 7 days > 2× the first-30-day mean (ramp present and material)
  - the ramp is **monotone-with-noise, not a step**: no single hour-over-hour jump exceeds 15% of range
  - PUMP-104A `temperature_c` cross-correlation with `vibration_hz` peaks at lag 3 h ± 1
  - `corr(feed_rate_tph, rotational_torque_nm)` ∈ `[0.65, 0.85]`
  - mean and σ of each pre-existing series within 5% of the `_original_` table

---

## Task 3: Metallurgy — enforce the two-product mass balance

* **Files**: create `data/generator/metallurgy.py`, `data/generator/tests/test_metallurgy.py`
* **Depends on**: Task 1
* **Deliverable**: rewritten `metallurgical_recovery` and `crusher_states` where recovery is **computed, not drawn**.

  Generate feed grade `f` (OU, tracking ore delivered), concentrate grade `c`, and tailings grade `t`; then compute recovery by the two-product formula:

  ```
  R = 100 · c·(f − t) / ( f·(c − t) )
  ```

  Recovery ceases to be an independent random number and becomes what it actually is — a consequence of three measured grades. This alone converts the most exposed table in the dataset into one that survives inspection.

  **Calibration note.** Feeding today's *means* (`f` 1.1121, `c` 27.5795, `t` 0.0689) into the formula yields **R ≈ 94.0**, against a stored mean of 92.21 — a 1.8 pp gap that is itself evidence recovery was never computed. The generator holds `f` and `c` near their observed distributions and tunes the `t` distribution upward so the *computed* mean lands at 92.2 ± 0.3 and the range stays inside the observed 88.0 – 96.0. Recovery is never clipped to fit; if it leaves the band, the grade distributions are wrong and get fixed instead.

  **Excursion (A5).** A `crusher_states.gap_size_setting_mm` change drives coarser feed, which lifts `tailings_grade_pct`, which depresses recovery through the formula — a **causal chain S07 can discover**, not a correlation it has to assert.
* **Verification**:
  ```
  py312 -m pytest data/generator/tests/test_metallurgy.py -v
  ```
  Expected: recomputing `R` from `f`, `c`, `t` for every row reproduces the stored `recovery_rate_pct` to within 0.01 pp (**mass balance holds exactly**); `corr(recovery, tailings_grade)` < −0.6; `corr(recovery, feed_grade)` > 0.3; recovery stays within `[85, 97]`; the A5 excursion is present and traceable to a gap-size change.

---

## Task 4: Work-order economics

* **Files**: create `data/generator/maintenance.py`, `data/generator/tests/test_maintenance.py`
* **Depends on**: Task 1
* **Deliverable**: rewritten `erp_work_orders.repair_cost` and `maintenance_logs.actual_duration_hours` with cost built from its components rather than drawn independently:

  ```
  repair_cost = labour_rate · crew_size · actual_duration_hours
              + parts_cost(parts_replaced)
              + fixed_mobilisation
  ```

  `parts_cost` resolves through `work_order_parts_edge` → `inventory_levels.unit_price_usd`, so the number ties to real part prices. `crew_size` is **not a stored column** — it is derived deterministically from `priority` (CRITICAL 6, HIGH 4, MEDIUM 3, LOW 2) inside the generator, and `fixed_mobilisation` scales the same way.

  **Only 152 of the 500 work orders have a `maintenance_logs` row**, and those are exactly the `COMPLETED` ones. For the other 348 there is no duration to correlate against, so cost is drawn from the priority-conditional distribution the 152 imply. The cost/duration correlation test therefore runs on the 152-row join, which is the only place both quantities exist.

  **A second tell fixed here:** today mean cost is *inverted* against priority — LOW averages $6,381 while CRITICAL averages $6,160. Deriving cost from crew size and duration corrects the ordering as a by-product rather than by patching it.
* **Verification**:
  ```
  py312 -m pytest data/generator/tests/test_maintenance.py -v
  ```
  Expected: on the 152-row `erp_work_orders ⋈ maintenance_logs` join, `corr(repair_cost, actual_duration_hours)` ∈ `[0.70, 0.90]`; every `repair_cost` reproducible from its components to within $1; mean cost by priority ordered CRITICAL > HIGH > MEDIUM > LOW; total spend within 15% of the original **$3,007,375** so demo talking points survive; the 152 logged work orders remain exactly the `COMPLETED` ones.

---

## Task 5: Fatigue — correct the physiology and plant the A6 case

* **Files**: create `data/generator/fatigue.py`, `data/generator/tests/test_fatigue.py`
* **Depends on**: Task 1
* **Deliverable**: rewritten `biometric_fatigue_logs` and mirrored `fatigue_logs_node`.
  - **Fix the sign**: `heart_rate_bpm` rises with `sleep_deficit_hours` (target corr **+0.35 to +0.55**), reversing the measured −0.116.
  - `microsleep_events_detected` drawn from a Poisson whose rate increases with deficit — preserving the 0.466 relationship that already worked.
  - Circadian structure: deficits accumulate across consecutive night shifts and recover on days off. **`operator_vehicle_assignments` cannot drive this** — it holds 5 rows, all dated `2026-06-18`, which is *outside* the 167-day fatigue window. The generator therefore synthesises a rotating roster (14-day cycle: 7 day / 2 off / 5 night) across the 20 operators, and the 5 real assignment rows are honoured as the roster's final state rather than contradicted.
  - **A6 case**: **OP-113** — already a NIGHT-shift operator in `operator_vehicle_assignments` and already linked through `incident_involvements` to `INC-5059` on `TRUCK-03`. Using this operator means the fatigue trail leads to an incident that already exists, rather than requiring a new one. Their `sleep_deficit_hours` crosses 6 over consecutive nights approaching the incident date.
  - `heart_rate_bpm` is `INTEGER` — values are rounded, not stored as floats. Preserve the observed band (50–84, mean 71.7, σ 7.4) while reversing the correlation sign.
* **Verification**:
  ```
  py312 -m pytest data/generator/tests/test_fatigue.py -v
  ```
  Expected: `corr(sleep_deficit_hours, heart_rate_bpm)` ∈ `[0.35, 0.55]`; `corr(sleep_deficit_hours, microsleep_events_detected)` ∈ `[0.40, 0.60]`; `fatigue_alert_triggered` true for ≥ 90% of rows with deficit > 6; the A6 operator resolves through `MiningOperationsSafetyGraph` to a real incident; `fatigue_logs_node` and `biometric_fatigue_logs` agree row-for-row.

---

## Task 6: Supply-chain coupling (A4) — the cross-branch story

* **Files**: create `data/generator/supply_chain.py`, `data/generator/tests/test_supply_chain.py`
* **Depends on**: Tasks 2, 4
* **Deliverable**: `inventory_levels` stock positions driven below reorder point for parts that genuinely sit on the critical path of PUMP-104A's open work orders, **timed to coincide with the Task 2 degradation ramp**. The columns are `stock_level` and `reorder_point_limit` (not `quantity_on_hand` / `reorder_point`); below-ROP means `stock_level < reorder_point_limit`.

  This is the demo's central claim — *the predicted failure and the missing bearing are the same event* — and it must be true in the data rather than asserted in the narration.

  Consumption is modelled: `parts_replaced` history draws stock down, lead times govern replenishment, and 15 parts land below ROP as they do today, but now for a reason.
* **Verification**:
  ```
  py312 -m pytest data/generator/tests/test_supply_chain.py -v
  ```
  Expected: the S08 `GRAPH_TABLE` traversal from §3.2 of the design doc returns **≥ 1 path** from a below-ROP part through a work order to PUMP-104A — verified **by traversal, not by construction**; below-ROP count ∈ `[12, 18]`; ≥ 1 below-ROP part maps to a CRITICAL-rated asset; no negative stock levels.

---

## Task 7: Geology divergence (A7)

* **Files**: create `data/generator/geology.py`, `data/generator/tests/test_geology.py`
* **Depends on**: Task 1
* **Deliverable**: `drill_assay_logs` and `geological_block_models` sharing a spatial model — block estimates interpolated from nearby assays with realistic error, plus **one zone where assayed grades run materially below the model**, giving S06 something to find. Grades follow a lognormal distribution (as ore grades do), not the near-uniform spread they have today.

  **The spatial join has to be constructed, because no coordinate column exists on the assays.** `drill_assay_logs` carries only `drill_hole_id` and `depth_start_meters` / `depth_end_meters`. Every hole in `drill_holes` is vertical (`dip_degrees = −90`, `azimuth 0` for all 30), so an assay interval's position is `(collar_easting, collar_northing, collar_elevation − mean_depth)`. That places assays in the same frame as `geological_block_models.centroid_x/y/z` (x 485100–486000, y 7432100–7433000, z 325–550) and makes inverse-distance interpolation possible.

  Grade columns are `drill_assay_logs.gold_grade_gpt` and `geological_block_models.gold_grade_gpt_est`. Rock type is `geology_code` on assays and `lithology_type` on blocks — the same five values (`OVERBURDEN`, `GRANITE`, `QSP_ORE`, `BASALT`, `CHERT`), which today carry **no grade signal at all** (means 0.376–0.407 across all five). Real deposits are lithology-controlled; `QSP_ORE` should be the ore host and carry materially higher gold than `OVERBURDEN`.
* **Verification**:
  ```
  py312 -m pytest data/generator/tests/test_geology.py -v
  ```
  Expected: outside the divergent zone, correlation between an assay's `gold_grade_gpt` and its nearest block's `gold_grade_gpt_est` > 0.6; inside it, assayed gold averages ≥ 25% below modelled; `QSP_ORE` mean gold ≥ 2× `OVERBURDEN` mean in both tables; `specific_gravity` differs by `lithology_type` beyond noise; the gold-grade distribution passes a lognormality check (it currently does not).

---

## Task 8: Load, with reversibility proven

* **Files**: create `data/generator/load.py`, `data/generator/run_all.py`
* **Depends on**: Tasks 2–7
* **Deliverable**: one command regenerates and loads everything. Load order is dependency-correct: dimensions, then facts, then edges. Uses `bq load` with explicit schema; partitioning and clustering preserved exactly.
* **Verification**:
  ```
  py312 data/generator/run_all.py --dry-run   # writes to *_staging_, touches nothing live
  py312 data/generator/run_all.py --apply
  ```
  Expected: staging row counts match targets; after apply, every rewritten table's schema is byte-identical to its `_original_` (compared via `INFORMATION_SCHEMA.COLUMNS`); a documented rollback command restores from `_original_` and is **executed once in dry-run to prove it works**.

---

## Task 9: The realism suite — one gate over everything

* **Files**: create `data/generator/tests/test_realism.py`
* **Depends on**: Task 8
* **Deliverable**: the four failing tests from §0, re-run against the loaded data as a single pass/fail gate, plus the graph probes.

  | # | Assertion |
  |---|---|
  | R1 | lag-1 autocorrelation ∈ `[0.75, 0.95]` for every asset·metric |
  | R2 | diurnal amplitude > 3% of mean for every continuous series |
  | R3 | two-product mass balance holds to 0.01 pp on every metallurgy row |
  | R4 | `corr(repair_cost, duration)` ∈ `[0.70, 0.90]` |
  | R5 | `corr(sleep_deficit, heart_rate)` ∈ `[0.35, 0.55]` |
  | R6 | all four property graphs traverse and return **> 0 rows** |
  | R7 | no NULLs in key columns; no negative stock, duration, or cost |
  | R8 | every summary statistic quoted in the PRD still holds, or the PRD is updated in the same commit |
* **Verification**:
  ```
  py312 -m pytest data/generator/tests/test_realism.py -v
  ```
  Expected: **8/8 PASS**. R6 is the explicit guard against the workflow's named trap — a property graph over empty tables succeeds silently, so a zero-row result fails the build rather than passing quietly.

---

## Task 10: Retrain BQML models against data that now has signal

* **Files**: create `data/models/retrain.sql`, `data/models/tests/test_models.py`
* **Depends on**: Task 9
* **Deliverable**: the four `downtime_regression_model*` models retrained on telemetry that now contains a degradation trend, and `safety_model` retrained on corrected fatigue physiology. Model *architecture* is unchanged — only training data. `asset_clustering_model` and `inventory_impact_model` retrained for consistency.
* **Verification**:
  ```
  bq query --use_legacy_sql=false < data/models/tests/eval.sql
  ```
  Expected: `ML.EVALUATE` on each downtime model shows R² materially above its pre-retrain value (recorded before retraining for comparison); `ML.PREDICT` on PUMP-104A in the ramp window returns a shorter time-to-failure than in the flat window. The second assertion is the real test — it is the difference between a model that learned the trend and one that memorised the mean.

---

## Ordering constraint

```
Task 1 ──┬─ Task 2 ─┐
         ├─ Task 3  │
         ├─ Task 4 ─┼─→ Task 6 ─→ Task 8 ─→ Task 9 ─→ Task 10
         ├─ Task 5  │
         └─ Task 7 ─┘
```

Tasks 2–5 and 7 are independent and testable alone. Task 6 depends on 2 and 4 because the coupling it creates spans both. Nothing loads until 8; nothing is trusted until 9.

**This satisfies the non-negotiable Phase 5 ordering** — data model, then data, then load, then graph verification, then agents. Agents are not in this plan and will not be started until Task 9 is green.

---

## Out of scope

- Agent implementation — a separate plan after Task 9.
- Schema changes, new tables beyond the three additive ones in Phase 3 §1.4.
- Replacing BQML model architectures; only retraining.
- Sub-hourly telemetry, vibration harmonics, or FFT spectra — not supportable at hourly sampling and will not be faked.

---

## Gate

This is the last gate before code. Approve and I start at Task 1.
