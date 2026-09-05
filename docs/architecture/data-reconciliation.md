# Data reconciliation — declared vs real

The agent catalogue declares 34 source tables. Before this work **26 did not exist**, 
and **65 of 101 agents had no readable grounding at all**.


The names were written against a medallion lakehouse (`mining_lakehouse_bronze/silver/gold`) 
specified in the vault's technical architecture and **never built** — the project has no such 
dataset. Two names, `plant_telemetry` and `crusher_telemetry`, appear in no vault document at all.


Nothing caught it. The repo enforces `assert_reads_only_declared_tables` on its own SQL — all 40 
method-pack files pass — but the vendored catalogue was imported as trusted data when it is really 
a set of assertions, and assertions need tests.


## How each declared table now resolves

| Declared table | Agents | Resolution | Source | Rows |
| --- | ---: | --- | --- | ---: |
| `assay_logs` | 4 | view | drill_assay_logs | 0 |
| `assets` | 14 | native | — | 5 |
| `blast_designs` | 6 | generated | anchored to geological_block_models block ids | 180 |
| `crusher_telemetry` | 8 | view | crusher_states | 0 |
| `dispatch_routes` | 2 | view | haulage_routes + haul_cycle_log | 0 |
| `drill_holes` | 5 | native | — | 30 |
| `erp_work_orders` | 3 | native | — | 500 |
| `explosives_inventory` | 2 | generated | anchored to named blasting consumables | 7 |
| `fatigue_monitoring_logs` | 1 | view | biometric_fatigue_logs | 0 |
| `financial_ledger` | 1 | view | contained_metal_price_deck + invoices | 0 |
| `fleet_telemetry` | 10 | view | telemetry_stream (TRUCK) + fleet_vehicles | 0 |
| `flotation_assays` | 4 | view | metallurgical_recovery | 0 |
| `geological_block_models` | 4 | native | — | 1000 |
| `geotech_sensors` | 3 | generated | anchored to pit bench locations from haulage_routes | 240 |
| `invoices` | 3 | native | — | 175 |
| `lube_samples` | 2 | generated | anchored to assets + maintenance_logs work orders | 220 |
| `mine_production_schedule` | 4 | view | plan_versions + plan_assumptions | 0 |
| `pit_designs` | 3 | view | geological_block_models | 0 |
| `plant_telemetry` | 15 | view | telemetry_stream (CONVEYOR/MILL/PUMP/CRUSHER assets) | 0 |
| `port_vessels` | 5 | generated | anchored to rail_schedules consists | 40 |
| `purchase_orders` | 3 | generated | anchored to inventory_levels parts + contracts vendors | 180 |
| `qaqc_standards` | 1 | view | drill_assay_logs (assayed intervals) | 0 |
| `rail_schedules` | 3 | generated | anchored to stockpiles | 120 |
| `reagent_inventory` | 3 | generated | anchored to named flotation reagents | 10 |
| `safety_permits` | 3 | view | safety_incidents | 0 |
| `safety_telemetry` | 2 | view | safety_incidents | 0 |
| `spares_inventory` | 6 | view | inventory_levels | 0 |
| `stockpiles` | 3 | generated | anchored to real stockpile locations + block-model grade | 8 |
| `survey_scans` | 1 | generated | anchored to geological_block_models block ids | 120 |
| `tenement_leases` | 1 | generated | anchored to block-model extents | 6 |
| `tsf_piezometers` | 4 | generated | anchored to Tailings Gate locations | 200 |
| `vendor_contracts` | 6 | view | contracts + contract_clauses | 0 |
| `vibration_monitors` | 1 | view | telemetry_stream (vibration_hz) | 0 |
| `water_balance_logs` | 3 | generated | anchored to metallurgical_recovery timestamps | 167 |

## Rules applied

**A view is a rename plus an honest filter, never a synonym.** `geotech_sensors` was drafted as a view over `telemetry_stream` and withdrawn: that table carries temperature, vibration, belt tension, payload, engine temperature, load, speed, power draw, rotational speed, torque and feed rate — and no geotechnical metric whatsoever. It is generated instead.


**An empty view is worse than a missing table.** `reagent_inventory`, `explosives_inventory` and `lube_samples` were built as filtered views and returned zero rows: `inventory_levels` holds spares only, and `technician_notes` is boilerplate. An agent facing an empty table stops saying *no such table* and starts reporting *no data*, which reads as a finding about the mine. All three were withdrawn and generated.


**Generated rows anchor to real entities.** Blast designs key to real `block_id`s; piezometers to the real Tailings Gate; water balance to real `metallurgical_recovery` timestamps; rail loads out of real stockpiles and vessels load the rail that arrives. Every join resolves — verified, not assumed.


## Guards

`tests/integrity/test_declared_tables_exist.py`, all mutation-tested:

| Test | Catches |
| --- | --- |
| every declared source table exists | the 26 dead tables |
| no agent is left without grounding | the 65 ungrounded agents |
| no declared table is empty | the empty-view trap |
| the front end publishes only real provenance | Screen 4 rendering fiction |
| the catalogue model resolves at the configured location | the `gemini-3.7-flash` region 404 that broke all 91 engines |