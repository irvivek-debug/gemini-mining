# Agent Recordings — Sales Companion

One entry per agent. Each recording opens on the operational question,
shows the agent reading BigQuery live (the tool trace), then scrolls
the answer at reading pace.

**Demo-day notes.**

- *Latency truth.* Agents answer in seconds via the API but typically
  2–4 minutes through the chat UI, and under sustained load the wait
  lands before the agent starts work — a longer timeout does not help.
  Pre-warm the agent you plan to show, or narrate the tool trace: it is
  the proof of grounding, and it is the part worth talking over.
- *Fallback order.* Play the recording first — it is verified and it
  cannot stall. Go live only on request, and only for an agent you
  pre-warmed. If the UI is queuing, drop to the API, which answers in
  seconds and shows the same grounding without the chat surface.

## Strategic Planning Advisor (AGT-19)

*Commercial/Finance/Strategy — CEO / CFO / Executive Committee*

**Situation.** Pit 4 copper price projection drops 15% from $4.20/lb to $3.57/lb. With mining cost $3.10/t, milling cost $14.50/t, and 89.5% recovery, calculate dynamic Kenneth Lane cut-off grade sensitivity. **Agent Action.** It looks up the geological block model, the financial ledger and the mine production schedule — the operation's live data, not a briefing pack — and answers in its own words: “Strategic Planning Advisory Report” It reports real figures — 4.20, 9,259.42, 9,323.40 — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/AGT-19/page@034c1ca6db082835450fa94388d4ae76.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/2639398376744540579/session/-

## Core Image Segmenter (D01)

*Exploration/Geology — Elena (Mine Geologist)*

**Situation.** Calculate RQD on drill core tray #104 with lengths [12, 18, 8, 22, 14, 5, 25]cm on 120cm run. **Agent Action.** It looks up drill hole records — the operation's live data, not a briefing pack — and answers in its own words: “Core Image Segmentation & RQD” It reports real figures — 75.83%, 86.67% — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/D01/page@00ead87e481d9c97351fdf3a0a50f2ee.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/7961791724780686286/session/-

## Hyperspectral Mineral Mapper (D02)

*Exploration/Geology — Geochemist*

**Situation.** Extract sericite vs illite crystallinity ratio from 2200nm SWIR spectral reflection. **Agent Action.** It looks up drill hole records and assay results — the operation's live data, not a briefing pack — and answers in its own words: “Based on an inspection of the project database (your-gcp-project-id.mining_data), here is the spectral feature extraction evaluation and data” It reports real figures — 1.743%, 1.213, 1.192% — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/D02/page@1ed6e647f025e88506843263040609d1.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/905468479589496947/session/-

## JORC Classification Auditor (D03)

*Exploration/Geology — Competent Person*

**Situation.** Audit drill spacing confidence for 25x25m vs 50x50m drill grids. **Agent Action.** It looks up drill hole records and the geological block model — the operation's live data, not a briefing pack — and answers in its own words: “JORC Mineral Resource Classification Audit: Drill Spacing Confidence” It reports real figures — 8,509.43, 0.30, 4.0 — pulled from the data during the recording. **Logic.** Before answering it runs its Spatial Drill Spacing Confidence Index method, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/D03/page@68b64c6ed94cebda026b1a557be6a23d.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/4649342689434985829/session/-

## Blast Wave Front Sim (D04)

*Mine Planning/Operations — D&B Specialist*

**Situation.** Calculate CJ detonation pressure for emulsion with density 1.18 g/cm3 and VOD 5400 m/s. **Agent Action.** It looks up blast designs — the operation's live data, not a briefing pack — and answers in its own words: “1. Data Reconciliation &” It reports real figures — 1.18, 3.0, 8.602 — pulled from the data during the recording. **Logic.** Before answering it runs its Chapman-Jouguet Detonation Hugoniot Solver method, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/D04/page@a8d67caa7071bde5702b06c660a63e3e.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/17821761931664506582/session/-

## Flyrock Trajectory Predictor (D05)

*Mine Planning/Operations — Shotfirer*

**Situation.** Compute maximum flyrock travel distance for 45 deg ejection angle at v0=42 m/s. **Agent Action.** It looks up blast designs — the operation's live data, not a briefing pack — and answers in its own words: “The maximum horizontal travel distance $R$ for a ballistic projectile (flyrock) is determined by the standard ballistic range” It reports real figures — 9.81, 1.0, 179.82 — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/D05/page@595eb7a439c834db268a8e2919a34c65.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/12044950816072083474/session/-

## In-Situ Fragment Analyzer (D06)

*Mine Planning/Operations — D&B Engineer*

**Situation.** Fit Rosin-Rammler muckpile curve for xc=120mm and uniformity index n=1.15. **Agent Action.** It looks up blast designs — the operation's live data, not a briefing pack — and answers in its own words: “Rosin-Rammler Muckpile Fragmentation Curve” It reports real figures — 63.21%, 1.15, 141.84 — pulled from the data during the recording. **Logic.** Before answering it runs its Split-Desktop High-Res Image Segmentation method, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/D06/page@b14b427713b787531a8d8d47dbaad4b6.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/17733897435877732313/session/-

## Radar Slope Displacement (D07)

*Mine Planning/Operations — Geotech Engineer*

**Situation.** Calculate Fukuzono inverse velocity failure time for 14 mm/day bench creep. **Agent Action.** It looks up geotechnical sensor readings — the operation's live data, not a briefing pack — and answers in its own words: “1. Reconciling Supplied Assumption vs. Operational Data” It reports real figures — 6.341, 6.008, 6.28 — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/D07/page@858fc33d0c28bc46198ee88e74ff6a3e.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/5771882020233678970/session/-

## Borehole Seismicity Sentinel (D08)

*Mine Planning/Operations — Microseismic Technician*

**Situation.** Compute microseismic b-value for 120 seismic events on North Pit fault. **Agent Action.** It looks up geotechnical sensor readings — the operation's live data, not a briefing pack — and answers in its own words: “Borehole Seismicity Sentinel Report” It reports real figures — 2.40, 6.01, 35.9 — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/D08/page@8de16710f4d9ddb411d395072a2772e0.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/16222986639730781285/session/-

## Bench Drainage Permeability (D09)

*Mine Planning/Operations — Hydrogeologist*

**Situation.** Calculate discharge rate for 12 horizontal drain holes with k=1e-5 m/s. **Agent Action.** It looks up pit designs — the operation's live data, not a briefing pack — and answers in its own words: “1. Verification and Reconciliation Against” It reports real figures — 2.52, 2.75, 0.864 — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/D09/page@3decbde598fc487ba82a6b49730f4902.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/1371995073496644570/session/-

## Haul Road Rolling Resist (D10)

*Fleet/Haulage — Civil Road Superintendent*

**Situation.** Calculate rimpull requirement for CAT 797F (550t GMW) on 8% ramp with 3% rolling resistance. **Agent Action.** It looks up live fleet telemetry — the operation's live data, not a briefing pack — and answers in its own words: “1. Reconciliation of Assumptions Against Operational” It reports real figures — 205.02, 130.63, 239.97 — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/D10/page@112a90fa3cf58bf4231f9d983dd380c0.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/10833388638952133340/session/-

## Fleet Fuel Burn Sentinel (D11)

*Fleet/Haulage — Energy Manager*

**Situation.** From fleet telemetry, list the haul-cycle metrics we actually record for the truck fleet with latest values — show them. Compute the fuel-efficiency measure this data genuinely supports, in plain arithmetic, and state plainly which additional logging a full litres-per-tonne-kilometre figure would need. **Agent Action.** It looks up live fleet telemetry — the operation's live data, not a briefing pack — and answers in its own words: “1. Haul-Cycle Metrics Recorded in Fleet” It reports real figures — 240.0, 218.40, 32.50 — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/D11/page@bd0b9d1a815749e2fd65596269f58272.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/13101384251525449016/session/-

## Tire TKPH Telemetry Agent (D12)

*Fleet/Haulage — Mobile Fleet Maintenance Lead*

**Situation.** Calculate tire TKPH for 238t payload at 24 km/h average cycle speed. **Agent Action.** It looks up live fleet telemetry — the operation's live data, not a briefing pack — and answers in its own words: “Tire TKPH Telemetry” It reports real figures — 238.00, 205.02, 130.63 — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/D12/page@cf5c703f217391780cabe5eb785f1071.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/9758962924959748081/session/-

## Shovel GET Tooth Sentinel (D13)

*Fleet/Haulage — Shovel Operator*

**Situation.** Screen fleet telemetry for Shovel #04: list every metric we record with its latest value and the unit's operational status, and flag any metric whose latest reading sits more than 3 standard deviations from its trailing mean — show the values. State plainly which failure modes (for example a lost ground-engaging tooth) this data can and cannot detect, and name the instrument that would close the gap. **Agent Action.** It looks up live fleet telemetry — the operation's live data, not a briefing pack — and answers in its own words: “1. Telemetry Screening for Shovel” It reports real figures — 42.0, 339.6, 97.1 — pulled from the data during the recording. **Logic.** Before answering it runs its YOLOv8 Ground Engaging Tool Watcher method, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/D13/page@c03630720d779285ed985b4905b96920.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/6134679660633629158/session/-

## Autogenous Grinding Sound (D14)

*Mineral Processing/Plant — Mill Operator*

**Situation.** Analyze SAG mill acoustic FFT power spectrum at 1200-2400 Hz. **Agent Action.** It looks up plant telemetry — the operation's live data, not a briefing pack — and answers in its own words: “Agent Profile & Methodological” It reports real figures — 3.500, 4.086, 4.700 — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/D14/page@2adebb6dcaacf7168cf8eb158d3a20e7.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/17829819385329910239/session/-

## Trommel Screen Blinding (D15)

*Mineral Processing/Plant — Concentrator Technician*

**Situation.** From plant telemetry around the SAG discharge, list the recorded metrics and trend the most relevant one over the last 30 days — show the values. Screen blinding is not directly instrumented: say so plainly, state what the throughput and power readings can and cannot tell us about a discharge restriction, and name the single measurement that would settle it. **Agent Action.** It looks up plant telemetry — the operation's live data, not a briefing pack — and answers in its own words: “1. Recorded Metrics Around the SAG Discharge” It reports real figures — 3.911, 14.504, 4.491 — pulled from the data during the recording. **Logic.** Before answering it runs its Aperture Occlusion Optical Flow Percentage method, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/D15/page@61bb2dbf0916815bc7c778da7cce8a5b.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/6344681735013446444/session/-

## Slurry Pump Cavitation (D16)

*Mineral Processing/Plant — Fixed Plant Fitter*

**Situation.** Calculate available Net Positive Suction Head for slurry pump #3 at 65% solids. **Agent Action.** It looks up plant telemetry — the operation's live data, not a briefing pack — and answers in its own words: “1. Telemetry Reconciliation & Data” It reports real figures — 65.4, 968.8, 6.2 — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/D16/page@73fc59d1bbc646ec7e4269446a724d37.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/3255539541494084213/session/-

## Sump Level Anti-Surge (D17)

*Mineral Processing/Plant — Process Control Specialist*

**Situation.** Regulate sump level PID speed for 3,800 tph feed slurry surge. **Agent Action.** It looks up plant telemetry — the operation's live data, not a briefing pack — and answers in its own words: “Sump Level Anti-Surge Control Action” It reports real figures — 3,800 tph, 1,153.25 tph, 1,000.56 tph — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/D17/page@89fefc6559ab1b69e68c690418453929.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/7025307563315550538/session/-

## Froth Bubble Sizing/Color (D18)

*Mineral Processing/Plant — Flotation Technician*

**Situation.** From flotation assays, report current feed grade, concentrate grade, tailings grade and recovery — show the values and verify recovery with a plain two-product check, no formula notation. Bubble-size instrumentation is absent: say so plainly, then quantify how far today's recovery sits below the best 30-day recovery in the data and what that gap is worth in contained-metal terms, quoted as a range. **Agent Action.** It looks up flotation assay results and plant telemetry — the operation's live data, not a briefing pack — and answers in its own words: “Current Flotation Assays &” It reports real figures — 1.09%, 26.20%, 0.076% — pulled from the data during the recording. **Logic.** Before answering it runs its Sauter Mean Bubble Diameter d32 & RGB Grade Proxy method, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/D18/page@42000aabfaa834385253bc258475ee9a.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/17273012408267433389/session/-

## Xanthate Degradation (D19)

*Mineral Processing/Plant — Reagent Chemist*

**Situation.** Calculate potassium amyl xanthate (PAX) potency after 72 hours storage at 32 deg C. **Agent Action.** It looks up reagent stock levels — the operation's live data, not a briefing pack — and answers in its own words: “1. Operational Inventory” It reports real figures — 7 days, 57.54, 305.15 — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/D19/page@e4704920adb01abc9087341ef137c114.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/2463177645997507271/session/-

## Acid Mine Drainage ORP (D20)

*Mineral Processing/Plant — Environmental Superintendent*

**Situation.** Calculate hydrated lime Ca(OH)2 dosage to neutralize pit sump pH from 3.2 to 7.5. **Agent Action.** It looks up water balance logs — the operation's live data, not a briefing pack — and answers in its own words: “Hydrated Lime $\text{Ca(OH)}_2$ Neutralization” It reports real figures — 74.093, 3.2, 6.3096 — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/D20/page@6c5a4b520f167bfafd4e819079d9e929.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/1126839582103419021/session/-

## Tailings Beach Slope (D21)

*Mineral Processing/Plant — TSF Engineer*

**Situation.** Predict beach slope angle for thickened tailings with yield stress 65 Pa. **Agent Action.** It looks up tailings dam sensor readings — the operation's live data, not a briefing pack — and answers in its own words: “1. Governing Method & Deposition” It reports real figures — 45.10, 79.20, 119.60 — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/D21/page@c8593eb65ef461c6a4f98bc4cbfdd352.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/5611152752644422239/session/-

## Transformer Dissolved Gas (D22)

*Asset Integrity/Maintenance — HV Electrician*

**Situation.** From the assets register, report the Main Substation transformer record in full: type, criticality rating, installation date, current state and stored physics parameters — show them, and compute its age in years in plain arithmetic. Dissolved-gas readings are not in this estate: state that plainly and recommend the monitoring addition, using the criticality rating as the business justification. **Agent Action.** It looks up the asset register — the operation's live data, not a briefing pack — and answers in its own words: “Asset Record: Main Substation” It reports real figures — 8.38, 65.0, 0.0403 — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/D22/page@42338f126c38f31a8de9ca7065e8abf7.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/17610690989667960583/session/-

## Motor Partial Discharge (D23)

*Asset Integrity/Maintenance — Electrical Engineer*

**Situation.** Analyze stator winding partial discharge for 15 MW SAG mill synchronous motor. **Agent Action.** It looks up the asset register — the operation's live data, not a briefing pack — and answers in its own words: “1. Operational Asset Reconciliation & Technical” It reports real figures — 4.0, 4.5, 4.25 — pulled from the data during the recording. **Logic.** Before answering it runs its High-Frequency Transient Phase-Resolved PD method, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/D23/page@a61ab03fb218d0f47afe89ca55af6d9e.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/5183629188203019270/session/-

## Conveyor Belt Rip Ultra (D24)

*Asset Integrity/Maintenance — Belt Splicer Lead*

**Situation.** Monitor ultrasonic sensor array on 4km overland coarse ore conveyor CV-01. **Agent Action.** It looks up the asset register — the operation's live data, not a briefing pack — and answers in its own words: “Conveyor Belt Rip Ultra (Agent d24) — Asset & Sensor Monitoring” It reports real figures — 116.8045, 23.1614, 5.24 — pulled from the data during the recording. **Logic.** Before answering it runs its Time-of-Flight Acoustic Wave Attenuation method, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/D24/page@f6711ae44cf24e85365e5ea0813341cc.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/12470560680853903472/session/-

## Chute Wear Ultrasonic (D25)

*Asset Integrity/Maintenance — Boilermaker Lead*

**Situation.** From the assets register, report the primary crusher's record: type, criticality rating, installation date, current state and stored physics parameters — show them, and compute the asset's age in years in plain arithmetic. Liner thickness is not instrumented here: state that plainly, and recommend an inspection cadence justified by the age and criticality you just computed. **Agent Action.** It looks up the asset register — the operation's live data, not a briefing pack — and answers in its own words: “Primary Crusher Asset” It reports real figures — 116.8532, 23.1189, 4205.0 — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/D25/page@d144b56260041be84b49918c2ffff276.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/5181698511014105791/session/-

## Maintenance Work Backlog (D26)

*Asset Integrity/Maintenance — Tom (Maintenance Planner)*

**Situation.** Calculate schedule float for SAG mill liner replacement critical path. **Agent Action.** It looks up open work orders — the operation's live data, not a briefing pack — and answers in its own words: “Critical Path Method (CPM) Schedule Float” It reports real figures — 0.00 — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/D26/page@0e6f0137e680900e40fd6023711ffbf2.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/424629171197778528/session/-

## Contractor Idle Fee Audit (D27)

*Commercial/Finance/Strategy — Commercial Manager*

**Situation.** Audit 48 hours standby claim for contractor dozer fleet against FMS GPS movement. **Agent Action.** It looks up supplier contracts and live fleet telemetry — the operation's live data, not a briefing pack — and answers in its own words: “Contractor Idle Fee Audit” It reports real figures — 48 hours, 162.18, 1,156.81 — pulled from the data during the recording. **Logic.** Before answering it runs its Standby Hours vs Daily Rate Dispute Validator method, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/D27/page@c525c326c2c75f33d6d1654db9cb044f.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/14871181550156206719/session/-

## Fuel Bunkering Density (D28)

*Commercial/Finance/Strategy — Fuel Logistics Officer*

**Situation.** Calculate temperature-corrected diesel fuel volume for 120,000L bunkering at 34 deg C. **Agent Action.** It looks up purchase-order history — the operation's live data, not a briefing pack — and answers in its own words: “1. Data Reconcilement & Operational” It reports real figures — 141.5, 131.5, 0.840 — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/D28/page@17de5aa53388596bcbb70d73d399e130.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/8219039806167601700/session/-

## Grinding Ball Wear Batch (D29)

*Asset Integrity/Maintenance — Plant Metallurgist*

**Situation.** From plant telemetry, report the mill's average power draw in megawatts — show the value and the reading count behind it. Using a stated media wear rate of 45 grams per kilowatt-hour, compute daily grinding ball consumption in tonnes per day in plain arithmetic, no formulas. Then check spares inventory for grinding media and state how many days the current stock covers. **Agent Action.** It looks up spare parts stock and plant telemetry — the operation's live data, not a briefing pack — and answers in its own words: “Based on operational records in plant_telemetry for asset MILL-01 (metric_name =” It reports real figures — 4.086, 4.08603934, 0.16 — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/D29/page@8b9ce19bf0bb522155fc21ab47f8eee3.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/16177627500456872112/session/-

## Lube Oil Cleanliness (D30)

*Asset Integrity/Maintenance — Tribologist*

**Situation.** Parse particle count data for SAG mill pinion lube oil reservoir. **Agent Action.** It looks up the asset register and oil sample analyses — the operation's live data, not a briefing pack — and answers in its own words: “Asset Name: SAG Grinding Mill 1 (Pinion / Drive Lubrication” It reports real figures — 49.2, 14.9, 16.0 — pulled from the data during the recording. **Logic.** Before answering it runs its ISO 4406 Solid Contamination Cleanliness Code method, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/D30/page@6820cfea700bf9cee726173e630d1c49.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/3203587165096507461/session/-

## Consignment Stock Logger (D32)

*Supply Chain/Logistics — Warehouse Clerk*

**Situation.** Reconcile warehouse RFID scan against SAP goods issue for 12 pump seals. **Agent Action.** It looks up spare parts stock — the operation's live data, not a briefing pack — and answers in its own words: “Reconciliation Summary: Warehouse RFID Scan vs. SAP Movement Type 201 Goods” It reports real figures — 450.00, 900.00, 7 days — pulled from the data during the recording. **Logic.** Before answering it runs its RFID Tag vs SAP Movement Type 201 Reconciler method, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/D32/page@fc9808e548fe33c5bee633aa66438356.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/4122039674810283352/session/-

## Laytime BIMCO Parser (D33)

*Supply Chain/Logistics — Logistics Officer*

**Situation.** Parse port laytime statement for 'MV Bulk Pioneer' under rain interruptions. **Agent Action.** It looks up vessel movements at the port — the operation's live data, not a briefing pack — and answers in its own words: “Laytime & Statement of Fact (SOF) Parsing” It reports real figures — 75,542.0, 9.73%, 10.0% — pulled from the data during the recording. **Logic.** Before answering it runs its BIMCO Laytime Standard Statement of Fact Parser method, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/D33/page@ff59967d22a5db0eabfb22deb9006155.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/583739645883463374/session/-

## Reagent Shelf Life (D34)

*Supply Chain/Logistics — Hazmat Technician*

**Situation.** List every xanthate-class collector in reagent inventory with stock level, reorder point, lead time and unit price — show the numbers. Then, using this stated rule of thumb — 6 months usable life at 20 C, halved for every 10 C above 20 C — work out usable life at 38 C storage in plain arithmetic (no formulas), and the dollar value of stock at risk if we cannot consume it in that window. **Agent Action.** It looks up reagent stock levels — the operation's live data, not a briefing pack — and answers in its own words: “Xanthate-Class Collector” It reports real figures — 7 days, 57.54, 51,037.98 — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/D34/page@addc4908d57ffeb033140b879ebe3c7c.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/8228845743322555862/session/-

## Locomotive Brake Curve (D35)

*Supply Chain/Logistics — Rail Master*

**Situation.** Calculate stopping distance for 12,000t loaded ore train at 60 km/h on 0.5% grade. **Agent Action.** It looks up rail schedules — the operation's live data, not a briefing pack — and answers in its own words: “Operational Reconciliation & Data” It reports real figures — 061.8, 920.4, 911.7 — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/D35/page@c6434a46b46457e8990cfd2308292013.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/13394976667368344513/session/-

## Shiploader 3D LiDAR (D36)

*Supply Chain/Logistics — Shiploader Operator*

**Situation.** For every vessel currently in port, compare cargo moisture percentage against its Transportable Moisture Limit and report the safety margin in percentage points — show the values per vessel and flag any within 1 point of the limit. State plainly that boom-clearance monitoring is not in this dataset, and confirm which loading-safety checks this data does support. **Agent Action.** It looks up vessel movements at the port — the operation's live data, not a briefing pack — and answers in its own words: “Operational Context & Sentinel” It reports real figures — 5.0, 1.00, 9.00% — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/D36/page@827b2c2853d79934121e44dfb72594f2.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/17690808582680002326/session/-

## SAFTE Driver Fatigue (D37)

*Safety/OHSE/ESG — Jack (Mine Safety Lead)*

**Situation.** Calculate SAFTE bio-mathematical fatigue score for operator on 4th night shift. **Agent Action.** It looks up fatigue monitoring logs records — the operation's live data, not a briefing pack — and answers in its own words: “Biomathematical SAFTE Fatigue Evaluation (Operator on 4th Night” It reports real figures — 2.13 hours, 2.06, 1.04 — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/D37/page@6936de6c8068a73e4cd8fba794576449.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/4130455342070868544/session/-

## Confined Space Gas (D38)

*Safety/OHSE/ESG — Industrial Hygienist*

**Situation.** From safety telemetry, report all recorded incidents around the mill and plant: count by severity level, the locations involved, and how many investigations are still open — show the numbers. Gas readings are not logged in this estate: state that plainly, then argue from the incident history whether the confined-space liner inspection should proceed and what monitoring must be in place first. **Agent Action.** It looks up safety telemetry — the operation's live data, not a briefing pack — and answers in its own words: “1. Telemetry and Gas Monitoring” It reports real figures — 63.3%, 19.5%, 23.5% — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/D38/page@6855588a2dd6db0da1f892461cb90b88.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/10224314405726841486/session/-

## Carbon Scope 1/2 Tracker (D39)

*Safety/OHSE/ESG — Sustainability Lead*

**Situation.** From fleet and plant telemetry, total the energy-related metrics the data actually holds, month by month — show the monthly values. Using a stated grid factor of 0.7 kg CO2 per kilowatt-hour, compute the carbon measure the data supports in plain arithmetic, quoted as a range, and name exactly which missing inputs — fuel litres, cathode tonnes — would complete a per-tonne intensity figure. **Agent Action.** It looks up live fleet telemetry and plant telemetry — the operation's live data, not a briefing pack — and answers in its own words: “1. Reconciling Telemetry Data & Governing” It reports real figures — 0.7, 0.700, 2 hours — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/D39/page@1a441ac668c2203cd9ce5bac8eb3de64.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/9664629732570460254/session/-

## Statutory Permit Guardian (D40)

*Safety/OHSE/ESG — Legal Counsel & Compliance Officer*

**Situation.** Audit statutory environmental water discharge permit expiry timelines. **Agent Action.** It looks up tenement leases records and safety permits records — the operation's live data, not a briefing pack — and answers in its own words: “Executive Summary & Regulatory Audit” It reports real figures — 10,885.50, 417,265.21, 2,482.00 — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/D40/page@c0cab5bf484f0d244ffe3b98e0bed0d8.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/12178037606655907260/session/-

## Drill Lithology Specialist (S01-1-LITHOLOGY)

*Exploration/Geology — Exploration Geologist*

**Situation.** From drill_holes, profile the drilling campaign: hole count, total metres drilled, the depth distribution, and the azimuth and dip patterns — show the numbers. Piece-length logging for rock-quality classification is absent: say so plainly, then identify the three holes whose geometry makes them the best candidates for oriented-core re-logging, and why. **Agent Action.** It looks up drill hole records — the operation's live data, not a briefing pack — and answers in its own words: “1. Drilling Campaign” It reports real figures — 8,509.43, 151.73, 228.75 — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S01-1-LITHOLOGY/page@4feba7d4aaf8eba0adcdae97a5b91b07.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/5332440710463027597/session/-

## Assay Geostatistics Specialist (S01-2-GEOSTAT)

*Exploration/Geology — Geostatistician*

**Situation.** Compute estimation variance for copper block grades at Section 104N. **Agent Action.** It looks up assay results — the operation's live data, not a briefing pack — and answers in its own words: “Geostatistical Review & Reconciled” It reports real figures — 7,432,014.93, 7,432,993.81, 0.949% — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S01-2-GEOSTAT/page@8df2c03593acec88ed8341a311c0fe53.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/9087835982665536979/session/-

## Structural Fault Specialist (S01-3-STRUCTURAL)

*Exploration/Geology — Structural Geologist*

**Situation.** Analyze strike and dip planes on Section 104N fault envelope. **Agent Action.** It looks up the geological block model — the operation's live data, not a briefing pack — and answers in its own words: “Structural Fault Analysis: Section 104N Fault” It reports real figures — 0.4375, 0.50, 23.63 — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S01-3-STRUCTURAL/page@fef24161c391db7131ada37dfb2b83ab.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/2645900857098460761/session/-

## Geology Swarm Coordinator (S01-COORDINATOR)

*Exploration/Geology — Elena (Chief Mine Geologist)*

**Situation.** Synthesize Section 104N drillhole assays into Ordinary Kriging 3D block model. **Agent Action.** It looks up drill hole records, assay results and the geological block model — the operation's live data, not a briefing pack — and answers in its own words: “Synthesis of Section 104N Drillhole Assays into Ordinary Kriging 3D Block” It reports real figures — 485,148.11, 7,432,325.23, 532.80 — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S01-COORDINATOR/page@9a67f58d67441ab5bc0f1b851a57d618.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/2549813273247417527/session/-

## Resource Critic (JORC / QAQC Red Team) (S01-R-CRITIC)

*Exploration/Geology — Competent Person (CP / QP)*

**Situation.** Audit duplicate core sample assay variance against JORC Code standards. **Agent Action.** It looks up assay results and QA/QC standards — the operation's live data, not a briefing pack — and answers in its own words: “QA/QC Red Team Audit: Duplicate Core Sample Assay Variance & JORC Code” It reports real figures — 100.0%, 0.0, 447.75 — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S01-R-CRITIC/page@ff20a8ecab0d5ac93da59c36cd259473.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/13867639205775571505/session/-

## Pit Wall Geotechnical Specialist (S02-1-GEOTECH)

*Mine Planning/Operations — Geotechnical Engineer*

**Situation.** From the geotech sensors on the 48 degree wall section, report the actual readings: slope angle, displacement, pore pressure and alarm states — show them. Then compute the simple stability ratio this data supports using a stated assumption of 35 degrees friction angle, in plain arithmetic, give the result as a range, and let the displacement trend make the final call: safe to continue, or hold. **Agent Action.** It looks up geotechnical sensor readings — the operation's live data, not a briefing pack — and answers in its own words: “Geotechnical Assessment & Sensor” It reports real figures — 47.0, 49.0, 48.0 — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S02-1-GEOTECH/page@7c7cfd1d3c60bcf73b109b1a905b2e76.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/2467120801253827430/session/-

## Phase Scheduling Specialist (S02-2-SCHEDULE)

*Mine Planning/Operations — Long-Term Planning Engineer*

**Situation.** Sequence shovel assignments to balance 1.8 Mt/month ore extraction. **Agent Action.** It looks up the mine production schedule — the operation's live data, not a briefing pack — and answers in its own words: “Shovel Sequencing & Extraction” It reports real figures — 1.80, 1.180, 1.196 — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S02-2-SCHEDULE/page@ce6228cd49a014efb702ead23753615b.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/14750280296794731530/session/-

## Waste Dump Stability Specialist (S02-3-DUMP)

*Mine Planning/Operations — Civil Mine Engineer*

**Situation.** Model North Dump toe containment volume and runout angle of repose. **Agent Action.** It looks up pit designs — the operation's live data, not a briefing pack — and answers in its own words: “Waste Dump Geotechnical & Stability Report: North Dump Toe Containment & Runout” It reports real figures — 2.558, 25.10, 2.050 — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S02-3-DUMP/page@ae225950de128ccd7df3158d8719eaaf.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/14198794820232846068/session/-

## Mine Planning Coordinator (S02-COORDINATOR)

*Mine Planning/Operations — Planning Superintendent*

**Situation.** Optimize Phase 3 pushback extraction sequence with 48 deg overall slope. **Agent Action.** It looks up the mine production schedule and pit designs — the operation's live data, not a briefing pack — and answers in its own words: “1. Executive Optimization” It reports real figures — 48.0, 45.0, 9,323.40 — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S02-COORDINATOR/page@7efbdc19e61babee0642e9e4104662b8.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/10031640407747179171/session/-

## Plan Compliance Critic (Red Team) (S02-R-CRITIC)

*Mine Planning/Operations — Senior Mine Surveyor*

**Situation.** Audit spatial compliance between monthly extraction and long-term model. **Agent Action.** It looks up survey scans and the mine production schedule — the operation's live data, not a briefing pack — and answers in its own words: “Executive Summary & Red Team Audit” It reports real figures — 898,261.40, 903,312.60, 5,051.20 — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S02-R-CRITIC/page@1bf756eca21b1d7df15a1b28139ca4aa.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/6834062730278861341/session/-

## Blast Geometry Specialist (S03-1-GEOMETRY)

*Mine Planning/Operations — D&B Engineer*

**Situation.** From our blast design records, profile the geometry we actually drill: average burden, spacing, hole diameter and hole depth, and the recorded powder factor — show the values and verify the powder factor arithmetic in plain numbers. Then recommend a staggered pattern for a 15 m production bench that stays inside our own historical envelope, saying which numbers come from data and which are judgment. **Agent Action.** It looks up blast designs — the operation's live data, not a briefing pack — and answers in its own words: “Operational Blast Geometry” It reports real figures — 5.77, 4.01, 7.48 — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S03-1-GEOMETRY/page@421572ba51dbabfe17b6acf639e30158.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/6899800456415450209/session/-

## Explosives Energy Specialist (S03-2-EXPLOSIVE)

*Mine Planning/Operations — Shotfirer Technical Lead*

**Situation.** Calculate bulk emulsion VOD and shock energy partitioning. **Agent Action.** It looks up explosives inventory — the operation's live data, not a briefing pack — and answers in its own words: “1. Operational Context & Explosives Inventory” It reports real figures — 1.5, 129.64, 35.54 — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S03-2-EXPLOSIVE/page@83c90c3cd5c8ed412f0698769677ad4b.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/385821222619278877/session/-

## Blast Vibration Sentinel (S03-3-VIBRATION)

*Mine Planning/Operations — D&B Engineer*

**Situation.** From blast design records, compute the scaled distance from our typical charge to the crusher at 450 metres — plain arithmetic from the recorded hole geometry and powder factor, values shown. Site attenuation constants are uncalibrated: say so plainly, bound the expected vibration as a range using the standard published constants as a named assumption, and recommend the calibration blast that would make it exact. **Agent Action.** It looks up blast designs — the operation's live data, not a briefing pack — and answers in its own words: “1. Reconciliation of Assumptions Against Operations &” It reports real figures — 4.9, 5.77, 7.07 — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S03-3-VIBRATION/page@daecb9d01af18f2a367e5035cdd678e1.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/9816945852212110694/session/-

## Drill & Blast Coordinator (S03-COORDINATOR)

*Mine Planning/Operations — Drill & Blast Superintendent*

**Situation.** From approved blasts in our design records, show the actual range of burden and powder factor used, against the fleet average — values on screen. For a harder-than-average block, recommend how far to move burden and powder factor while staying inside the range our own data supports, with each calculation step shown in plain numbers, and confirm from explosives inventory that magazine stock covers the recommendation. **Agent Action.** It looks up blast designs and explosives inventory — the operation's live data, not a briefing pack — and answers in its own words: “1. Baseline Blast Design Parameters (Approved” It reports real figures — 4.01, 5.85, 7.48 — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S03-COORDINATOR/page@cee35447fd836eab3ba3da119fe503d6.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/6919052797483217132/session/-

## Blast Safety Critic (Red Team) (S03-R-CRITIC)

*Mine Planning/Operations — Statutory Shotfirer*

**Situation.** Enforce 500m blast exclusion perimeter and lightning warning gate. **Agent Action.** It looks up blast designs and safety permits records — the operation's live data, not a briefing pack — and answers in its own words: “Blast Safety Critic (Red Team) Gate” It reports real figures — 82.2%, 17.8%, 0.497 — pulled from the data during the recording. **Logic.** Before answering it runs its Statutory Exclusion Zone Radius & Misfire Detection Gate method, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S03-R-CRITIC/page@13e14ff4c82e44dad3287ce9f1c41067.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/3034965665875988605/session/-

## Shovel Match Specialist (S04-1-SHOVEL)

*Fleet/Haulage — Dispatch Controller*

**Situation.** Calculate pass match factor for PC8000 shovel loading CAT 797F. **Agent Action.** It looks up live fleet telemetry — the operation's live data, not a briefing pack — and answers in its own words: “Pass Match Factor Calculation: PC8000 Shovel & CAT” It reports real figures — 240.0 t, 205.02 t, 130.63 t — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S04-1-SHOVEL/page@20d64529b379c35428ef108e8138e14d.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/17491806829630784661/session/-

## Haul Route Optimizer (S04-2-ROUTE)

*Fleet/Haulage — Fleet Planner*

**Situation.** Compute shortest path travel time on Pit Alpha south ramp. **Agent Action.** It looks up dispatch routes — the operation's live data, not a briefing pack — and answers in its own words: “Route Optimization Formulation &” It reports real figures — 1,031.49, 11.57, 1.27 — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S04-2-ROUTE/page@7856e44b153ea048d02e56290afab239.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/2596064410481970294/session/-

## Truck Payload Sentinel (S04-3-PAYLOAD)

*Fleet/Haulage — Fleet Controller*

**Situation.** Audit 10/10/20 payload distribution across 42 haul cycles. **Agent Action.** It looks up live fleet telemetry — the operation's live data, not a briefing pack — and answers in its own words: “OEM 10/10/20 Payload Distribution” It reports real figures — 1.20, 240.00, 202.03 — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S04-3-PAYLOAD/page@81b7b977678a88905f3ab334a4808863.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/4572058693527972819/session/-

## Load & Haul Coordinator (S04-COORDINATOR)

*Fleet/Haulage — Dave (Dispatch Superintendent)*

**Situation.** Reassign haul trucks to eliminate 3-truck queue at Shovel 04. **Agent Action.** It looks up live fleet telemetry and dispatch routes — the operation's live data, not a briefing pack — and answers in its own words: “Dynamic Fleet Dispatch & Queue Optimization” It reports real figures — 116.8311, 23.1686, 42.0 — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S04-COORDINATOR/page@50fc06df2f6df347b1cdd9de31569522.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/156538017085304316/session/-

## Dispatch Safety Critic (Red Team) (S04-R-CRITIC)

*Fleet/Haulage — Mine Safety Lead*

**Situation.** Check operator shift hours and SAFTE circadian fatigue index. **Agent Action.** It looks up live fleet telemetry and safety telemetry — the operation's live data, not a briefing pack — and answers in its own words: “Operational & Fatigue Analysis” It reports real figures — 7.0, 4.1, 3.0 — pulled from the data during the recording. **Logic.** Before answering it runs its Haul Road Grade Braking Runaway Distance Envelope method, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S04-R-CRITIC/page@32ef3e442b31ba6b2384c2556e9857e2.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/408790626050543109/session/-

## Crusher CSS Specialist (S05-1-CSS)

*Mineral Processing/Plant — Crusher Technician*

**Situation.** Based on the crusher telemetry data, what hydraulic pressure setpoint does your governing method indicate for a closed-side setting of 135mm? Report the figures from the data and cite the table you read. **Agent Action.** It looks up crusher telemetry — the operation's live data, not a briefing pack — and answers in its own words: “Based on a review of the crusher telemetry dataset in BigQuery, here is the reconciliation of the figures and the operating” It reports real figures — 135 mm, 115 mm, 125 mm — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S05-1-CSS/page@c3b0bfd34be0d15bbf14c7eab3042a9e.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/14348532487284515913/session/-

## Feeder Speed Specialist (S05-2-FEED)

*Mineral Processing/Plant — Control Room Operator*

**Situation.** Regulate apron feeder PID loop for choke feeding conditions. **Agent Action.** It looks up crusher telemetry — the operation's live data, not a briefing pack — and answers in its own words: “Feeder Speed Specialist (s05_2_feed) — Operational Control” It reports real figures — 1,026.30, 1,153.23, 1,297.05 — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S05-2-FEED/page@999fad73fb7022da6dfe706a5e0707e5.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/5869281968369631097/session/-

## Mantle Wear Estimator (S05-3-WEAR)

*Mineral Processing/Plant — Fixed Plant Planner*

**Situation.** Predict remaining liner life on Hardox 500 concave plates. **Agent Action.** It looks up the asset register and crusher telemetry — the operation's live data, not a briefing pack — and answers in its own words: “Archard Wear Modeling” It reports real figures — 4.90, 5.10, 1,153.23 tph — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S05-3-WEAR/page@f7122f90f138fb320b084ea1a67705ea.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/13456155721035413965/session/-

## Primary Crushing Coordinator (S05-COORDINATOR)

*Mineral Processing/Plant — Fixed Plant Superintendent*

**Situation.** Crusher-03 mantle wear is at 78%; eddy-current sensor flags tramp iron. **Agent Action.** It looks up crusher telemetry and the asset register — the operation's live data, not a briefing pack — and answers in its own words: “Operational Assessment & Directives: Primary Crushing Coordinator” It reports real figures — 120.0 mm, 120 mm, 135 mm — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S05-COORDINATOR/page@658e50cf2bacc904f054804c13c337e4.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/15517074791576987099/session/-

## Tramp Metal Critic (Red Team) (S05-R-CRITIC)

*Mineral Processing/Plant — Electrical Superintendent*

**Situation.** Enforce auto-hold on uncrushable steel tooth detection in cavity. **Agent Action.** It looks up crusher telemetry — the operation's live data, not a briefing pack — and answers in its own words: “Interlock Gate Enforcement Notice: Tramp Iron Eddy-Current” It reports real figures — 1,153.23 tph, 1,026.30 tph, 1,297.05 tph — pulled from the data during the recording. **Logic.** Before answering it runs its Tramp Iron Eddy-Current Sensor Interlock Gate method, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S05-R-CRITIC/page@7512da8f923257b4409deab211e633f4.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/1150542196225760960/session/-

## SAG Mill Load Specialist (S06-1-SAG)

*Mineral Processing/Plant — Mill Operator*

**Situation.** From plant telemetry for the SAG mill, trend power draw, rotational speed and any vibration metrics over the last 30 days — show the values and flag any reading more than 3 standard deviations from its mean. Acoustic arrays are not installed: state that plainly, then argue from the recorded metrics alone whether current operation looks like liner wear, overload, or normal running. **Agent Action.** It looks up plant telemetry — the operation's live data, not a briefing pack — and answers in its own words: “Operational Assessment & Plant Telemetry Analysis: SAG Mill” It reports real figures — 30 days, 3.996, 0.362 — pulled from the data during the recording. **Logic.** Before answering it runs its Acoustic Toe Angle & Ball Charge Trajectory method, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S06-1-SAG/page@5d69c40bfeb8b55f1bd62bcc62325956.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/17267471152570781932/session/-

## Ball Mill Power Specialist (S06-2-BALL)

*Mineral Processing/Plant — Grinding Technician*

**Situation.** Calculate daily grinding media ball charge replenishment for 3,800 tph. **Agent Action.** It looks up plant telemetry — the operation's live data, not a briefing pack — and answers in its own words: “Operational Reconciliation & Baseline” It reports real figures — 3,800 tph, 1,153.25 tph, 1,000.56 — pulled from the data during the recording. **Logic.** Before answering it runs its Austin Population Balance Grinding Kinetics method, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S06-2-BALL/page@cd9dd569aa5adb6c24c5d7cf46c3416e.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/13921225072596694266/session/-

## Hydrocyclone Split Specialist (S06-3-CYCLONE)

*Mineral Processing/Plant — Slurry Specialist*

**Situation.** From plant telemetry, report what the grinding circuit actually records with latest values — show them. Cyclone geometry and operating pressure are not instrumented: say so plainly, then give an illustrative cut-size answer as a range using standard 10-inch cyclone geometry as a named assumption, in plain arithmetic, and specify the two measurements that would make it exact. **Agent Action.** It looks up plant telemetry — the operation's live data, not a briefing pack — and answers in its own words: “1. Actual Grinding Circuit” It reports real figures — 3.68, 3.6785, 14.80 — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S06-3-CYCLONE/page@db701ce1004ec5f335860561ccf09129.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/7787327341957815195/session/-

## Grinding & Milling Coordinator (S06-COORDINATOR)

*Mineral Processing/Plant — Concentrator Superintendent*

**Situation.** SAG Mill #2 power spikes to 14.8 MW, toe acoustic noise dampened. **Agent Action.** It looks up plant telemetry and the asset register — the operation's live data, not a briefing pack — and answers in its own words: “Operational Assessment & Coordination” It reports real figures — 14.8, 3.09, 4.0 — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S06-COORDINATOR/page@29905a526405f1f5a0b1a550833c6915.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/16231628556639519542/session/-

## Slurry Density Critic (Red Team) (S06-R-CRITIC)

*Mineral Processing/Plant — Process Chemist*

**Situation.** Check cyclone feed density and trunnion bearing lubrication. **Agent Action.** It looks up plant telemetry — the operation's live data, not a briefing pack — and answers in its own words: “Critical Evaluation: Cyclone Feed Density & Trunnion Bearing” It reports real figures — 85.20, 71.42, 65.01 — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S06-R-CRITIC/page@43366a1adf5e09faf6c4232aed9d8dbf.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/13013800279746514045/session/-

## Collector Dosing Specialist (S07-1-REAGENT)

*Mineral Processing/Plant — Flotation Technician*

**Situation.** From reagent inventory, report our MIBC frother position — stock level, reorder point, lead time and dollar value — showing the numbers. Then state in plain arithmetic how far current stock sits above or below the reorder point, and what that gap is worth in dollars. **Agent Action.** It looks up reagent stock levels — the operation's live data, not a briefing pack — and answers in its own words: “Based on the data retrieved from your-gcp-project-id.mining_data.reagent_inventory, here is the position report for MIBC Frother 200L (Part Number:” It reports real figures — 21 days, 75.00, 56,550.00 — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S07-1-REAGENT/page@5ae813c47cc410987d11367935e39d90.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/12936409017092172708/session/-

## Froth Air Specialist (S07-2-AIR)

*Mineral Processing/Plant — Plant Metallurgist*

**Situation.** Regulate superficial gas velocity Jg across rougher bank. **Agent Action.** It looks up plant telemetry — the operation's live data, not a briefing pack — and answers in its own words: “Supervisory Control & Gas Holdup Profile: Rougher Bank Air” It reports real figures — 1,153.25 tph, 1,000.56, 1,299.86 tph — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S07-2-AIR/page@972d9b9e73cd200b1fe255468304dafd.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/13003249075149879793/session/-

## Concentrate Grade Specialist (S07-3-GRADE)

*Mineral Processing/Plant — Smelter Marketing Liaison*

**Situation.** Model cleaner bank separation efficiency for 28% Cu concentrate. **Agent Action.** It looks up flotation assay results — the operation's live data, not a briefing pack — and answers in its own words: “Separation Efficiency (SE) Model for 28.0% Cu” It reports real figures — 28.0%, 1.0929%, 0.81% — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S07-3-GRADE/page@eea13ed81a4ebd9fae30a863160e6093.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/3383821664191445726/session/-

## Flotation Recovery Coordinator (S07-COORDINATOR)

*Mineral Processing/Plant — Marcus (Chief Metallurgist)*

**Situation.** Optimize PAX collector dosing for 0.72% Cu ore to maximize recovery. **Agent Action.** It looks up flotation assay results and plant telemetry — the operation's live data, not a briefing pack — and answers in its own words: “Executive Optimization” It reports real figures — 0.72%, 1.09%, 0.81% — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S07-COORDINATOR/page@261075636ed411842acb0dc4c579ad5e.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/4100790245321040707/session/-

## Smelter Penalty Critic (Red Team) (S07-R-CRITIC)

*Mineral Processing/Plant — Commercial Metallurgist*

**Situation.** Check concentrate arsenic and bismuth penalty thresholds. **Agent Action.** It looks up flotation assay results — the operation's live data, not a briefing pack — and answers in its own words: “Smelter Penalty Critic (Red Team) Audit” It reports real figures — 27.41%, 24.99%, 30.16% — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S07-R-CRITIC/page@80a870494c8af7389801aac6e355fb4b.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/2422340200045156267/session/-

## Decant Water Return Specialist (S08-1-WATER)

*Mineral Processing/Plant — Water Treatment Operator*

**Situation.** Balance decant return water and evaporation pond volume. **Agent Action.** It looks up water balance logs — the operation's live data, not a briefing pack — and answers in its own words: “Decant Water Return & Evaporation Pond Water Balance” It reports real figures — 183,156.10, 1,096.74, 100.00% — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S08-1-WATER/page@e7ce39f43f2d297f74ed4bd5a5e58761.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/7388494887499711666/session/-

## Piezometer Pressure Specialist (S08-2-PORE)

*Mineral Processing/Plant — Geotech Instrumentation Tech*

**Situation.** From the TSF piezometers, trend pore pressure and phreatic surface by location across the full record — show the values and flag the worst factor-of-safety readings. Then estimate the dissipation timeline directly from the observed decay between readings, in plain arithmetic with no consolidation formulas, quote it as a range, and name the single lab parameter that would firm it up. **Agent Action.** It looks up tailings dam sensor readings — the operation's live data, not a briefing pack — and answers in its own words: “1. Executive Summary & Operational” It reports real figures — 61.10 kPa, 239.00 kPa, 154.67 kPa — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S08-2-PORE/page@401b56a0d7e38623d15ccc6dd19f15aa.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/17689915318949018488/session/-

## Slurry Thickener Specialist (S08-3-THICK)

*Mineral Processing/Plant — Dewatering Technician*

**Situation.** Regulate flocculant dosing for 65% solids underflow. **Agent Action.** It looks up plant telemetry — the operation's live data, not a briefing pack — and answers in its own words: “Operational Assessment & Telemetry” It reports real figures — 65.0%, 57.5%, 68.0% — pulled from the data during the recording. **Logic.** Before answering it runs its Kynch Sedimentation Solids Flux Theory method, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S08-3-THICK/page@b6b51b5b66296d293c2958dd89b8dd6f.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/2504307796515544315/session/-

## Tailings (TSF) Coordinator (S08-COORDINATOR)

*Mineral Processing/Plant — TSF Manager (Engineer of Record)*

**Situation.** Dam 2 piezometer reports pore pressure rise of 0.38m/week after rain. **Agent Action.** It looks up tailings dam sensor readings and water balance logs — the operation's live data, not a briefing pack — and answers in its own words: “Operational Reconciliation & Data” It reports real figures — 0.38, 2.65, 136.1 kPa — pulled from the data during the recording. **Logic.** Before answering it runs its GISTM Dam Conformance & Phreatic Surface Line method, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S08-COORDINATOR/page@64d10cb0d1e62f491e3debdbc274b351.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/5704906778757729715/session/-

## TSF Liquefaction Critic (Red Team) (S08-R-CRITIC)

*Mineral Processing/Plant — Statutory Geotechnical Reviewer*

**Situation.** Audit GISTM compliance and critical state soil mechanics. **Agent Action.** It looks up tailings dam sensor readings and safety permits records — the operation's live data, not a briefing pack — and answers in its own words: “Adversarial Geotechnical Audit: GISTM Compliance & Critical State Soil” It reports real figures — 1.30, 1.135, 16.0% — pulled from the data during the recording. **Logic.** Before answering it runs its Critical State Soil Mechanics & Static Liquefaction Index method, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S08-R-CRITIC/page@2798e977174e09f1670b2c957675267e.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/5536394081075780335/session/-

## Vibration FFT Specialist (S09-1-VIBRATION)

*Asset Integrity/Maintenance — Vibration Analyst (Category III)*

**Situation.** From crusher telemetry, trend rotational torque and feed rate over the last 30 days — show the values and flag any outlier beyond 3 standard deviations with its timestamp. Spectral vibration data is absent: say so plainly, then use the assets register's stored physics parameters to state which defect signature we would expect to see, whether the trend is consistent with it, and finish with a clear inspect or do-not-inspect call. **Agent Action.** It looks up the asset register and crusher telemetry — the operation's live data, not a briefing pack — and answers in its own words: “1. Telemetry Trend Analysis (Last 30” It reports real figures — 3,874.51, 145.47, 3,438.10 — pulled from the data during the recording. **Logic.** Before answering it runs its ISO 10816-3 RMS Velocity & BPFI Harmonics method, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S09-1-VIBRATION/page@b5cd24a925d2bd69fed814664007fde7.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/1209525171906486472/session/-

## Oil Tribology Specialist (S09-2-TRIBOLOGY)

*Asset Integrity/Maintenance — Lubrication Technician*

**Situation.** Evaluate Karl Fischer moisture and PQ particle quantifier index. **Agent Action.** It looks up the asset register and oil sample analyses — the operation's live data, not a briefing pack — and answers in its own words: “Executive Tribological” It reports real figures — 705.4, 0.0705%, 0.0 — pulled from the data during the recording. **Logic.** Before answering it runs its PQ Index & Karl Fischer Moisture PPM method, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S09-2-TRIBOLOGY/page@9071994a3f4ace9ba7013f550a0ea236.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/6541943629968723451/session/-

## Thermal IR Specialist (S09-3-THERMAL)

*Asset Integrity/Maintenance — Thermographer*

**Situation.** Analyze thermal gradient across pinion bearing housing. **Agent Action.** It looks up the asset register and crusher telemetry — the operation's live data, not a briefing pack — and answers in its own words: “Thermal IR Specialist Assessment: Pinion Bearing Housing Thermal Gradient” It reports real figures — 74.0, 4,205.0, 1,210.0 tph — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S09-3-THERMAL/page@adf03ed9998bf2b9715c7b17c2059362.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/12266523653873596783/session/-

## Asset Reliability Swarm Coordinator (S09-COORDINATOR)

*Asset Integrity/Maintenance — Priya (Reliability Superintendent)*

**Situation.** SAG Mill pinion bearing vibration reaches 4.8 mm/s RMS at 1480 RPM. **Agent Action.** It looks up the asset register, crusher telemetry and open work orders — the operation's live data, not a briefing pack — and answers in its own words: “Coordinator ID: s09_coordinator (Asset Reliability Swarm Coordinator / P0 Crisis Arbiter / Reliability” It reports real figures — 4.80 mm, 24.67, 14.8 — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S09-COORDINATOR/page@a79714db8f41a4bcb8df8f2118e01433.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/523079695801690856/session/-

## Maintenance Safety Critic (Red Team) (S09-R-CRITIC)

*Asset Integrity/Maintenance — Safety Supervisor*

**Situation.** Enforce Dual-Key HMAC MFA prior to staging SAP PM work pack. **Agent Action.** It looks up the asset register and open work orders — the operation's live data, not a briefing pack — and answers in its own words: “Maintenance Safety Critic (Red Team) — Safety Audit & Enforcement” **Logic.** Before answering it runs its LOTO Isolation Integrity & Failure Window Safety Gate method, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S09-R-CRITIC/page@1f7ede76f8dc75fc6b586cd1bdd08deb.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/3018210570239869511/session/-

## Contract Rate Auditor (S10-1-CONTRACT)

*Supply Chain/Logistics — Procurement Analyst*

**Situation.** Fuzzy-match line items against signed Master Service Agreement. **Agent Action.** It looks up supplier contracts — the operation's live data, not a briefing pack — and answers in its own words: “Contract Rate Auditor Audit” It reports real figures — 1,149.35, 390.23, 1,116.43 — pulled from the data during the recording. **Logic.** Before answering it runs its Levenshtein Distance & Unit Price Deviation method, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S10-1-CONTRACT/page@1be6f7d1713597ad1de131a36782d9db.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/4380926452236138549/session/-

## PPI Indexation Auditor (S10-2-ESCALATE)

*Supply Chain/Logistics — Commercial Specialist*

**Situation.** Compute labor and diesel escalation delta against PPI indices. **Agent Action.** It looks up supplier contracts — the operation's live data, not a briefing pack — and answers in its own words: “PPI Indexation Audit & Escalation” It reports real figures — 1.0, 1.00, 0.00 — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S10-2-ESCALATE/page@274fe2eac11a0d9003e90f56f6f36dde.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/15145174503599723797/session/-

## Warranty Recovery Specialist (S10-3-WARRANTY)

*Supply Chain/Logistics — Asset Accountant*

**Situation.** Audit SAG liner premature failure against 8,000-hour MTBF warranty. **Agent Action.** It looks up the asset register and supplier contracts — the operation's live data, not a briefing pack — and answers in its own words: “Executive Summary & Warranty Recovery” It reports real figures — 0.00 — pulled from the data during the recording. **Logic.** Before answering it runs its MTBF vs Warranty Period Recovery Claimer method, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S10-3-WARRANTY/page@3ce63f86dad9cc2307dda1cdb6831226.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/10236263633444215320/session/-

## Procurement Coordinator (S10-COORDINATOR)

*Supply Chain/Logistics — Sarah (Supply Chain Superintendent)*

**Situation.** Audit contractor haulage invoice #INV-8839 against signed MSA rate card. **Agent Action.** It looks up supplier contracts and invoices — the operation's live data, not a briefing pack — and answers in its own words: “Invoice Contract Matching & Rate Card Audit” It reports real figures — 58,549.56, 7.6 — pulled from the data during the recording. **Logic.** Before answering it runs its Invoice Contract Matching & Rate Card Variance method, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S10-COORDINATOR/page@9f65832d7bd76408e945ae4ef0fc04bd.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/5402454714704667630/session/-

## Anti-Bribery Audit Critic (Red Team) (S10-R-CRITIC)

*Supply Chain/Logistics — Internal Auditor*

**Situation.** Enforce FCPA compliance gate on sole-source supplier requisitions. **Agent Action.** It looks up supplier contracts and invoices — the operation's live data, not a briefing pack — and answers in its own words: “Anti-Bribery & FCPA Red Team Audit Report: Sole-Source Requisition & Vendor Compliance Gate” It reports real figures — 17,444.19, 5.0, 78,737.49 — pulled from the data during the recording. **Logic.** Before answering it runs its Vendor Beneficial Ownership & Single-Source Flags method, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S10-R-CRITIC/page@3c1e56250f0933e5bfa03a595810dac4.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/6963659721239708994/session/-

## Safety Stock Optimizer (S11-1-STOCK)

*Supply Chain/Logistics — Inventory Planner*

**Situation.** Calculate safety stock buffer for high-criticality bearings. **Agent Action.** It looks up spare parts stock — the operation's live data, not a briefing pack — and answers in its own words: “1. Spare Parts Inventory Status” It reports real figures — 14 days, 1,250.00, 0.00 — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S11-1-STOCK/page@f52b774e785783ac49732041df5f51bc.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/8952188845126189763/session/-

## Vendor Lead Time Specialist (S11-2-LEADTIME)

*Supply Chain/Logistics — Supply Expediter*

**Situation.** Model Gamma distribution supplier lead-time variability. **Agent Action.** It looks up purchase-order history — the operation's live data, not a briefing pack — and answers in its own words: “Gamma Distribution Supplier Lead-Time Variability” It reports real figures — 1 day, 15.04, 6.81 — pulled from the data during the recording. **Logic.** Before answering it runs its Gamma Distribution Lead Time Modeling method, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S11-2-LEADTIME/page@f76924ee707f8de0a0521b1475d45449.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/9319212464069988816/session/-

## Carrying Cost Analyzer (S11-3-HOLDING)

*Supply Chain/Logistics — Cost Controller*

**Situation.** Analyze working capital carrying cost on $45M MRO warehouse. **Agent Action.** It looks up spare parts stock — the operation's live data, not a briefing pack — and answers in its own words: “1. Assumption Reconciliation & Operational” It reports real figures — 45,000,000.00, 45.00, 55,879,117.67 — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S11-3-HOLDING/page@06bfb54fc61c16622252580c1401eefa.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/3626231911448469840/session/-

## Spares Inventory Coordinator (S11-COORDINATOR)

*Supply Chain/Logistics — Warehouse Superintendent*

**Situation.** Hydraulic cylinder stock is 0 with 8-week supplier lead time. **Agent Action.** It looks up spare parts stock and purchase-order history — the operation's live data, not a briefing pack — and answers in its own words: “Inventory Reconciliation & Operational” It reports real figures — 56 days, 7 days, 45 days — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S11-COORDINATOR/page@38a04bfed070d9966c86c1de17815738.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/2773276585102532221/session/-

## Dead Stock Critic (Red Team) (S11-R-CRITIC)

*Supply Chain/Logistics — Finance Auditor*

**Situation.** Flag non-moving spares (>365 days) for inventory buyback. **Agent Action.** It looks up spare parts stock — the operation's live data, not a briefing pack — and answers in its own words: “Dead Stock Critic (Red Team) Audit: Inactive Inventory Aging (>365 Days) & Buyback” It reports real figures — 2,880.00, 0.01%, 365 days — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S11-R-CRITIC/page@c380931bb3590a89297d73616fea1e8d.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/14327129105282995811/session/-

## Train Cycle Dispatch Specialist (S12-1-RAIL)

*Supply Chain/Logistics — Rail Controller*

**Situation.** Optimize train rake cycle time across 400km heavy-haul rail corridor. **Agent Action.** It looks up rail schedules — the operation's live data, not a briefing pack — and answers in its own words: “Operational Assessment & Train Rake Cycle Optimization (400 km Heavy-Haul” It reports real figures — 2,149,409.5, 17,911.75, 9,061.80 t — pulled from the data during the recording. **Logic.** Before answering it runs its Railway Headway & Velocity Optimization method, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S12-1-RAIL/page@9dea4b78667ca28b2aace1f7d1ff3fa3.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/17163419417666421589/session/-

## Port Stockpile Blend Specialist (S12-2-BLEND)

*Supply Chain/Logistics — Port Metallurgist*

**Situation.** Formulate LP blend model for 28.0% Cu export specification. **Agent Action.** It looks up stockpile records — the operation's live data, not a briefing pack — and answers in its own words: “Linear Programming (LP) Blend Model Formulation for 28.0% Cu Export” It reports real figures — 28.0%, 2,991,203.9, 0.4728% — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S12-2-BLEND/page@5ba0983f1623f42ff676b980b53d374f.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/17572349194673256958/session/-

## Marine Laytime & Demurrage Specialist (S12-3-BERTH)

*Supply Chain/Logistics — Marine Broker*

**Situation.** Compute BIMCO laytime Statement of Fact deductions. **Agent Action.** It looks up vessel movements at the port — the operation's live data, not a briefing pack — and answers in its own words: “Marine Laytime & Demurrage Statement of Fact (SOF)” It reports real figures — 2.0 days, 48 hours, 162 days — pulled from the data during the recording. **Logic.** Before answering it runs its BIMCO Laytime Pro-Rata & Demurrage Liability method, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S12-3-BERTH/page@af29d7a21db2cff25af36971ad923267.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/17205870215175020849/session/-

## Supply Chain & Port Coordinator (S12-COORDINATOR)

*Supply Chain/Logistics — Logistics Manager*

**Situation.** Vessel 'MV Cape Osprey' arrives in 48h for 160,000t loading. **Agent Action.** It looks up rail schedules, vessel movements at the port and stockpile records — the operation's live data, not a briefing pack — and answers in its own words: “Operational Assessment: Vessel 'MV Cape Osprey' Arrival & Dynamic Network” It reports real figures — 61,262.1, 24,431.6, 100,619.2 — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S12-COORDINATOR/page@d13366cf4830b9fc9911681da215c6da.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/15457650955703083468/session/-

## Moisture & TML Critic (Red Team) (S12-R-CRITIC)

*Supply Chain/Logistics — Cargo Surveyor*

**Situation.** Enforce IMSBC Transportable Moisture Limit (TML < 9.2%). **Agent Action.** It looks up vessel movements at the port and stockpile records — the operation's live data, not a briefing pack — and answers in its own words: “Governing Method &” It reports real figures — 9.20%, 10.00%, 9.73% — pulled from the data during the recording. **Logic.** Before answering it runs its governing calculation, checks any numbers given in the question against what the records actually say, points out any difference, and names the records behind every figure. If it cannot back something with data, it says so instead of guessing.

- **Recording:** `data/uat/videos/S12-R-CRITIC/page@9bbd5c6a6c454dc96ad235119a243140.webm`
- **Live agent:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/15122170761949992179/session/-
