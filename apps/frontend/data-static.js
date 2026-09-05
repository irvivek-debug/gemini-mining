/* Presentation content for Screens 2 and 3, transcribed verbatim from the
 * user's HTML 11.
 *
 * Hand-authored on purpose. Unlike window.agentCatalogData -- which is
 * generated from the agent registry by scripts/build_frontend_data.py -- these
 * two datasets have no upstream in the vault: they are the narrative the
 * design ships with. Stated here so nobody hunts for a generator that does not
 * exist, and so an edit here is understood as a content change, not a drift.
 *
 * Persona portraits are the URLs HTML 10 already shipped, copied from its own
 * personaData.avatar fields. They load from images.unsplash.com, so a persona
 * card falls back to its initials when the page is offline -- see the
 * .persona-hero-img / .persona-avatar-fallback pair in app.css.
 */

/* Screen 3 -- eight persona cockpits. */
window.personaPRDData = {
  elena: {
    avatar: "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=320&q=80",
    code: "P8 • EXPLORATION",
    title: "Elena Ramos, Chief Mine Geologist",
    mandate: "Mandate: Geological Resource Certainty, JORC 2012 Compliance, & Mine-to-Mill Grade Reconciliation",
    jtbd: "\"When assay batches arrive from Section 104N, synthesize lithology and ordinary kriging models into updated 3D block models in under 5 minutes, so that drill rigs can be redirected before wasting $85k/day on unmineralized waste clearance.\"",
    broken: "Elena spends 65% of her shift manually cross-referencing CSV assay tables, disjointed Vulcan wireframes, and handwritten core logs. Block model updates take 14 days, resulting in mining benches operating on outdated grade assumptions.",
    agentic: "S01 Geology Swarm continuously processes downhole telemetry, semivariograms, and hyperspectral core imagery. When variance exceeds 2 sigma, the swarm runs Ordinary Kriging in 11.4 seconds and emits an audited non-SCADA drill guidance proposal.",
    coordinatorId: "S01-COORDINATOR",
    squad: [
      { id: "S01-COORDINATOR", name: "Ore Block Lithology & Grade Reconciliation", apqc: "APQC 2.0.1", auth: "L2 ARBITER", desc: "Autonomous synthesis of multimodal core imagery, assays, and kriging models.", val: "+$85k/day" },
      { id: "S01-1-LITHOLOGY", name: "Hyperspectral Mineralogy Classifier", apqc: "APQC 2.0.1", auth: "SPECIALIST", desc: "Identifies alteration zones & clay fractions from core scans using Gemini Vision.", val: "+$1.2M/yr" },
      { id: "S01-2-GEOSTAT", name: "Dynamic Semivariogram & Kriging Engine", apqc: "APQC 2.0.1", auth: "SPECIALIST", desc: "Zero-hallucination spatial covariance & block grade estimation in 11.4s.", val: "+$2.4M/yr" },
      { id: "S01-3-STRUCTURAL", name: "Fault Discontinuity & Kinematic Solver", apqc: "APQC 2.0.1", auth: "SPECIALIST", desc: "Determines structural strike/dip slip planes for bench stability.", val: "+$950k/yr" },
      { id: "S01-R-CRITIC", name: "JORC 2012 Compliance Adversarial Critic", apqc: "APQC 2.0.1", auth: "RED-TEAM CRITIC", desc: "Stress-tests sample support volumes and rejects ungrounded grade claims.", val: "100% Audit Pass" }
    ]
  },
  marcus: {
    avatar: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=320&q=80",
    code: "P1 • FIXED PLANT RELIABILITY",
    title: "Marcus Vance, Plant Reliability Superintendent",
    mandate: "Mandate: Eliminate Catastrophic Mill Outages & Maximize Asset Health Across Grinding Circuit",
    jtbd: "\"When high-frequency vibration spikes on Crusher-03 pinions, execute sub-150ms ISO 10816 FFT vibration decomposition and stage an isolated SAP PM work pack before pinion tooth shearing causes a 72-hour unbudgeted plant shutdown.\"",
    broken: "Marcus juggles disjointed SCADA historians, 40-year-old vendor PDFs, and legacy PI alarms that trigger 3,200 nuisance notifications per shift, forcing reactive firefighting after physical asset failure.",
    agentic: "S05 Comminution Swarm with D26 Vibration Solver continuously processes 100Hz accelerometer feeds, autonomously detecting harmonic bearing wear 48 hours in advance and staging prioritized maintenance work packs.",
    coordinatorId: "S05-COORDINATOR",
    squad: [
      { id: "S05-COORDINATOR", name: "Primary Crusher Thermal & Kinetic Balancing", apqc: "APQC 3.2.1", auth: "L2 ARBITER", desc: "Monitors mantle temperature, eccentric pressure, and hydraulic tramp relief.", val: "+$3.8M/yr" },
      { id: "S05-1-CSS", name: "Gyratory Mantle Wear & CSS Optimizer", apqc: "APQC 3.2.1", auth: "SPECIALIST", desc: "Dynamically adjusts closed-side setting to maintain optimal product P80.", val: "+$1.4M/yr" },
      { id: "S05-2-FEED", name: "SAG-01 Shell Acoustics & Impact Energy", apqc: "APQC 3.2.1", auth: "SPECIALIST", desc: "Analyzes shell sound acoustics to prevent steel-on-steel ball impacts.", val: "+$2.1M/yr" },
      { id: "D26", name: "ISO 10816-3 FFT Vibration Severity Solver", apqc: "APQC 3.2.1", auth: "PHYSICS SOLVER", desc: "Deterministic Fourier transform decomposition for bearing inner/outer race faults.", val: "Zero Failure" },
      { id: "S05-R-CRITIC", name: "Thermal Runaway Adversarial Stress Critic", apqc: "APQC 3.2.1", auth: "RED-TEAM CRITIC", desc: "Validates thermocouple calibration drift vs ambient temperatures.", val: "Zero False Tripping" }
    ]
  },
  dave: {
    avatar: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=320&q=80",
    code: "P5 • PIT DISPATCH & HAULAGE",
    title: "Dave Miller, Mine Dispatch & Fleet Superintendent",
    mandate: "Mandate: Real-Time Shovel-Truck Fleet Queue Optimization & Payload Compliance",
    jtbd: "\"When Shovel-02 encounters high-silica hard rock benches, dynamically re-route 12 CAT 797F haul trucks to optimize crusher blend ratio and minimize queue starvation at the Primary Dump Pocket.\"",
    broken: "Dave monitors static dispatch screens and relies on radio chatter to balance 45 haul trucks across 4 pit benches, causing crusher starvation bottlenecks and $120k/week in idle fuel burn.",
    agentic: "S02 Mine Planning Swarm & S04 Haulage Swarm leverage Little's Law and stochastic queuing models to dynamically re-dispatch trucks every 30 seconds, eliminating shovel idle time and maximizing crusher blend consistency.",
    coordinatorId: "S04-COORDINATOR",
    squad: [
      { id: "S04-COORDINATOR", name: "Autonomous Haulage Fleet Dispatch Arbiter", apqc: "APQC 3.1.2", auth: "L2 ARBITER", desc: "Dynamic stochastic fleet allocation to eliminate shovel and crusher queues.", val: "+$4.2M/yr" },
      { id: "S04-1-SHOVEL", name: "Dynamic Bench-to-Crusher Match Factor", apqc: "APQC 3.1.2", auth: "SPECIALIST", desc: "Calculates instantaneous truck-shovel match factor to minimize queuing delays.", val: "+$1.8M/yr" },
      { id: "S04-2-ROUTE", name: "AHS Intersection & Speed Profiler", apqc: "APQC 3.1.2", auth: "SPECIALIST", desc: "Optimizes haul road speed profiles and retarder braking along switchbacks.", val: "+$920k/yr" },
      { id: "D09", name: "Little's Law & Stochastic Queuing Solver", apqc: "APQC 3.1.2", auth: "PHYSICS SOLVER", desc: "Deterministic queue length and cycle time solver: L = λ * W.", val: "-74% Queuing" },
      { id: "S04-R-CRITIC", name: "Haul Road Safety & Grade Critic", apqc: "APQC 3.1.2", auth: "RED-TEAM CRITIC", desc: "Verifies brake temperature dissipation envelopes and wet road friction limits.", val: "Zero Incident" }
    ]
  },
  sarah: {
    avatar: "https://images.unsplash.com/photo-1580489944761-15a19d654956?w=320&q=80",
    code: "P7 • RAIL & PORT LOGISTICS",
    title: "Sarah Jenkins, Supply Chain & Port Logistics Director",
    mandate: "Mandate: Pit-to-Port Synchronization, Demurrage Elimination & TML Safety Compliance",
    jtbd: "\"When train rake arrivals are delayed by track maintenance, dynamically reschedule ship loading sequences and port stockpile reclaimers so that Capesize vessels depart within the laycan window without incurring $45k/day demurrage.\"",
    broken: "Sarah coordinates rail manifests via disconnected spreadsheets and phone calls with track operators. Moisture spikes in port stockpiles risk liquefaction during maritime transit.",
    agentic: "S12 Pit-to-Port Swarm and ROC-02 Arbiter continuously synchronize train cycle times, stockyard moisture profiles, and vessel ETA telemetry, eliminating $2.4M/year in demurrage fines.",
    coordinatorId: "S12-COORDINATOR",
    squad: [
      { id: "S12-COORDINATOR", name: "Port Demurrage & Berth Allocation Arbiter", apqc: "APQC 4.4.1", auth: "L2 ARBITER", desc: "Optimizes vessel laycan schedules, shiploader rates, and train dump slotting.", val: "+$5.8M/yr" },
      { id: "S12-1-RAIL", name: "Heavy-Haul Rail Rake Cycle Optimizer", apqc: "APQC 4.4.1", auth: "SPECIALIST", desc: "Coordinates 240-car train schedules across passing loops.", val: "+$2.6M/yr" },
      { id: "S12-2-BLEND", name: "Port Stockpile Moisture & Grade Blending", apqc: "APQC 4.4.1", auth: "SPECIALIST", desc: "Maintains uniform concentrate grade and prevents Transportable Moisture Limit breach.", val: "+$1.9M/yr" },
      { id: "D33", name: "Discrete-Event Demurrage Laytime Solver", apqc: "APQC 4.4.1", auth: "PHYSICS SOLVER", desc: "Calculates exact vessel turnaround time and laytime penalties.", val: "Zero Demurrage" },
      { id: "S12-R-CRITIC", name: "Transportable Moisture Limit (TML) Critic", apqc: "APQC 4.4.1", auth: "RED-TEAM CRITIC", desc: "Enforces strict IMSBC Code moisture thresholds to eliminate cargo liquefaction risk.", val: "100% Maritime Safety" }
    ]
  },
  tariq: {
    avatar: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=320&q=80",
    code: "P2 • DYNAMIC THROUGHPUT BALANCING",
    title: "Tariq Al-Mansoor, Shift Operations Controller",
    mandate: "Mandate: Mine-to-Mill Mass Balance, Surge Bin Equilibrium, & Bond Energy Optimization",
    jtbd: "\"When feed ore Bond Work Index increases to 18.4 kWh/t, dynamically adjust crusher Closed Side Setting (CSS) from 160mm to 135mm and balance SAG mill feed rate to maintain stable 3,800 TPH plant throughput.\"",
    broken: "Tariq monitors 14 separate SCADA screens and makes manual setpoint changes that lead to surge bin overfills, feeder stalls, and SAG mill overload cycles.",
    agentic: "ROC-01 Arbiter and S06 Comminution Swarm continuously evaluate ore hardness and feed size distributions, executing sub-second setpoint balancing to maximize recovery.",
    coordinatorId: "ROC-01",
    squad: [
      { id: "ROC-01", name: "Crusher–Mill Throughput Balance Coordinator", apqc: "APQC 3.3.1", auth: "L1 ARBITER", desc: "Dynamic Bond energy balancing between primary crusher and grinding circuits.", val: "+$3.8M/yr" },
      { id: "S06-1-SAG", name: "SAG Mill 1/3-Octave Acoustic Shell Optimizer", apqc: "APQC 3.3.1", auth: "SPECIALIST", desc: "Interprets acoustic frequency response to prevent steel-on-liner impacts.", val: "+$4.2M/yr" },
      { id: "S06-3-CYCLONE", name: "Hydrocyclone Cut-Size d50c Classifier", apqc: "APQC 3.3.1", auth: "SPECIALIST", desc: "Optimizes circulating load and overflow particle size (P80 = 75 µm).", val: "+$2.7M/yr" },
      { id: "D14", name: "Bond Comminution Specific Energy Solver", apqc: "APQC 3.3.1", auth: "PHYSICS SOLVER", desc: "Deterministic power requirement: W = 10 * Wi * (1/sqrt(P80) - 1/sqrt(F80)).", val: "-18% Specific kWh/t" },
      { id: "S06-R-CRITIC", name: "Mill Slurry Pooling Adversarial Critic", apqc: "APQC 3.3.1", auth: "RED-TEAM CRITIC", desc: "Detects slurry pooling and overfilling before mill torque trip.", val: "Zero Mill Overload" }
    ]
  },
  priya: {
    avatar: "https://images.unsplash.com/photo-1573497019940-1c28c88b4f3e?w=320&q=80",
    code: "P3 • MINERAL PROCESSING & FLOTATION",
    title: "Dr. Priya Sharma, Chief Metallurgist & Flotation Specialist",
    mandate: "Mandate: Flotation Yield Recovery Uplift, Reagent Optimization & Concentrate Grade Compliance",
    jtbd: "\"When altered clay content in mill feed degrades froth stability, dynamically adjust collector dosing and air flow rate across 12 rougher cells to uplift recovery by +1.8% without diluting concentrate grade.\"",
    broken: "Priya relies on 4-hour assay turnaround delays and visual froth inspection, leading to excessive xanthate reagent consumption and $3.2M/yr in tailings losses.",
    agentic: "S07 Flotation Swarm uses computer vision bubble velocity analysis and Garcia-Zuniga kinetics solvers to continuously optimize air-reagent balance across all flotation banks.",
    coordinatorId: "S07-COORDINATOR",
    squad: [
      { id: "S07-COORDINATOR", name: "Rougher–Cleaner Flotation Recovery Arbiter", apqc: "APQC 3.3.2", auth: "L2 ARBITER", desc: "Multi-bank air addition, frother dosing, and pulp level coordination.", val: "+$7.4M/yr" },
      { id: "S07-1-REAGENT", name: "Collector/Frother Stoichiometric Dispenser", apqc: "APQC 3.3.2", auth: "SPECIALIST", desc: "Adjusts reagent dosage based on feed sulfur/iron ratios and particle size.", val: "+$1.9M/yr" },
      { id: "S07-2-AIR", name: "Garcia-Zuniga Recovery Kinetics Engine", apqc: "APQC 3.3.2", auth: "SPECIALIST", desc: "Estimates mineral flotation rate constants in real time.", val: "+$3.2M/yr" },
      { id: "D18", name: "Garcia-Zuniga First-Order Flotation Kinetics Solver", apqc: "APQC 3.3.2", auth: "PHYSICS SOLVER", desc: "R = R_inf * (1 - exp(-k * t)). Deterministic recovery yield curve.", val: "+1.8% Recovery" },
      { id: "S07-R-CRITIC", name: "Tailings Grade Loss & Scavenger Critic", apqc: "APQC 3.3.2", auth: "RED-TEAM CRITIC", desc: "Audits scavenger tailings grade and triggers reagent boost before unrecoverable loss.", val: "Zero Grade Breach" }
    ]
  },
  chen: {
    avatar: "https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?w=320&q=80",
    code: "P4 • TSF & ENVIRONMENTAL",
    title: "Chen Wei, Tailings & Environmental Compliance Lead",
    mandate: "Mandate: Global Industry Standard on Tailings Management (GISTM) Compliance & Zero Dam Failures",
    jtbd: "\"When piezometer pore pressure in TSF Cell-3 rises by 12% following a storm event, dynamically calculate slope Factor of Safety and redirect slurry spigot deposition before embankment instability threatens downstream watersheds.\"",
    broken: "Chen manually reviews monthly geotechnical reports and piezometer logs, missing localized pore pressure spikes and operating with delayed environmental audit visibility.",
    agentic: "S08 Tailings Swarm with the Bishop Slope Stability Solver continuously processes InSAR satellite telemetry, piezometer feeds, and water balance models to guarantee FoS > 1.50.",
    coordinatorId: "S08-COORDINATOR",
    squad: [
      { id: "S08-COORDINATOR", name: "TSF GISTM Geotechnical Compliance Arbiter", apqc: "APQC 3.8.1", auth: "L2 ARBITER", desc: "Autonomous tailings deposition, beach width management, and pore pressure tracking.", val: "+$3.9M/yr" },
      { id: "S08-3-THICK", name: "Tailings Thickener Underflow Density Control", apqc: "APQC 3.8.1", auth: "SPECIALIST", desc: "Maintains 68% solids paste underflow density to maximize water recovery.", val: "+$2.1M/yr" },
      { id: "S08-1-WATER", name: "Durand Slurry Pipeline Critical Velocity Guard", apqc: "APQC 3.8.1", auth: "SPECIALIST", desc: "Prevents solids settling and pipeline sanding in the overland slurry conduit.", val: "+$1.4M/yr" },
      { id: "D21", name: "Bishop Simplified Limit Equilibrium Slope Stability Solver", apqc: "APQC 3.8.1", auth: "PHYSICS SOLVER", desc: "Deterministic Factor of Safety calculation.", val: "FoS > 1.50" },
      { id: "S08-R-CRITIC", name: "TSF Liquefaction & Overtopping Adversarial Critic", apqc: "APQC 3.8.1", auth: "RED-TEAM CRITIC", desc: "Stress-tests embankment stability under extreme rainfall simulations.", val: "Zero Dam Incident" }
    ]
  },
  claire: {
    avatar: "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=320&q=80",
    code: "P6 • STRATEGIC CAPITAL & NPV",
    title: "Claire Dupont, Enterprise Financial Planning & Risk Officer",
    mandate: "Mandate: Dynamic Kenneth Lane Cut-Off Grade Optimization, Class A/B/C EBITDA Value Capture",
    jtbd: "\"When commodity prices fluctuate and power tariffs spike, dynamically solve Kenneth Lane cut-off grade equations to maximize 10-year discounted cash flow NPV across the 30-year mine plan.\"",
    broken: "Claire operates static annual financial models that lock in suboptimal cut-off grades for 12 months, leaving $84.2M in annual EBITDA value uncaptured across fluctuating price cycles.",
    agentic: "AGT-19 Strategic Planning Advisor continuously reconciles mill capacity, mining rates, and market forward curves to deliver dynamic NPV-maximizing operating setpoints.",
    coordinatorId: "AGT-19",
    squad: [
      { id: "AGT-19", name: "Strategic Planning Advisor & Capital Allocator", apqc: "APQC 1.1.1", auth: "L0 STRATEGIC", desc: "Enterprise-wide NPV optimization and dynamic Kenneth Lane cut-off grade arbiter.", val: "+$14.2M/yr" },
      { id: "ROC-03", name: "Clean Energy & Peak Demand Arbiter", apqc: "APQC 9.4.1", auth: "L1 ARBITER", desc: "Microgrid solar PV, BESS, and grinding circuit load shedding optimization.", val: "+$1.9M/yr" },
      { id: "S10-1-CONTRACT", name: "Contractor MSA Rate Variance Recovery", apqc: "APQC 4.1.2", auth: "SPECIALIST", desc: "Audits maintenance contractor invoices and equipment billing rates.", val: "+$2.4M/yr" },
      { id: "D02", name: "Kenneth Lane Cut-Off Grade NPV Maximizer", apqc: "APQC 1.1.1", auth: "PHYSICS SOLVER", desc: "Solves g_opt = argmax NPV(g, M, C, R) across life-of-mine cash flows.", val: "+$14.2M NPV Lift" },
      { id: "S10-R-CRITIC", name: "Statutory Financial & Anti-Bribery Compliance Critic", apqc: "APQC 1.1.1", auth: "RED-TEAM CRITIC", desc: "Stress-tests capital allocations against statutory auditing mandates.", val: "100% SOX Compliance" }
    ]
  }
};

/* Screen 2 -- the thirteen value-chain nodes.
 *
 * Keyed `flot`, not `flotation`: HTML 10 and HTML 11 disagreed on this one id,
 * and Screen 2 is built from HTML 10, so HTML 10's key governs. Getting this
 * wrong renders an empty inspector on the one node the whole flotation story
 * hangs off, so it is called out rather than left to be rediscovered.
 */
window.nodePRDData = {
  pita: {
    title: "Pit Alpha Operations (North Bench)", tag: "ISA-95: AURORA.MINE.PIT-ALPHA",
    health: "OPTIMAL", healthClass: "badge-optimal",
    swarm: "S01-GEOLOGY-ASSAY", coord: "S01-COORDINATOR (Ore Block Lithology)",
    solver: "D01: Geological Block Model Interpolation",
    formula: "Grade(x,y,z) = ∑ [w_i * Assay_i] / ∑ w_i | Density = 2.78 t/m³",
    sap: "STG-091-PITA-DISPATCH-01",
    metrics: [
      { key: "Extraction Rate", val: "6,200 TPH" },
      { key: "Head Grade", val: "0.48 %" },
      { key: "Bond Work Index (Wi)", val: "18.4 kWh/t" },
      { key: "Bench Elevation", val: "1,420 m RL" },
      { key: "Shovel Match Factor", val: "1.04 (Balanced)" }
    ]
  },
  pitb: {
    title: "Pit Beta Operations (South Valley)", tag: "ISA-95: AURORA.MINE.PIT-BETA",
    health: "OPTIMAL", healthClass: "badge-optimal",
    swarm: "S02-MINE-PLANNING", coord: "S02-COORDINATOR (Pushback & Strip Ratio)",
    solver: "D02: Kenneth Lane Cut-Off Grade Optimization",
    formula: "g_m = c / (P - s) | Optimal Cut-off: 0.38% (+$14.2M NPV)",
    sap: "STG-092-PITB-DISPATCH-02",
    metrics: [
      { key: "Extraction Rate", val: "4,800 TPH" },
      { key: "Head Grade", val: "0.54 %" },
      { key: "Bond Work Index (Wi)", val: "16.2 kWh/t" },
      { key: "Bench Elevation", val: "1,280 m RL" },
      { key: "Strip Ratio (W:O)", val: "2.4 : 1" }
    ]
  },
  sh05: {
    title: "Electric Rope Shovel SH05", tag: "ISA-95: AURORA.MINE.SHOVEL-SH05",
    health: "RUNNING", healthClass: "badge-optimal",
    swarm: "S04-LOAD-AND-HAUL", coord: "S04-COORDINATOR (Bucket Fill & Hang Time)",
    solver: "D08: Shovel Payload & Diggability Energy",
    formula: "DigEnergy = ∫ [V(t) * I(t)] dt / Payload_t | Fill Factor = 0.94",
    sap: "STG-095-SH05-TEETH-WEAR",
    metrics: [
      { key: "Payload Capacity", val: "120 t (54 m³)" },
      { key: "Loading Rate", val: "4,120 TPH" },
      { key: "Cycle Time", val: "26.4 sec / swing" },
      { key: "Hoist Motor Current", val: "1,420 A" },
      { key: "Bucket Teeth Wear", val: "14% Remaining Life" }
    ]
  },
  trks: {
    title: "Autonomous Haul Fleet (42x Cat 797F)", tag: "ISA-95: AURORA.MINE.FLEET-AHS",
    health: "OPTIMAL", healthClass: "badge-optimal",
    swarm: "S04-LOAD-AND-HAUL", coord: "S04-COORDINATOR (Queue Dispatch Arbiter)",
    solver: "D09: Littles Law Dynamic Fleet Dispatch",
    formula: "L = λ * W | Queue_Wait = 1.2 min | Velocity = 24.8 km/h",
    sap: "STG-098-TRK-TYRE-TKPH",
    metrics: [
      { key: "Active Haul Units", val: "42 Units (380t Payload)" },
      { key: "Haul Cycle Distance", val: "4.8 km one-way" },
      { key: "Fleet Availability", val: "94.2 %" },
      { key: "Tyre TKPH Rating", val: "640 TKPH" },
      { key: "Bypass Routing", val: "Crusher-03 Direct Dump" }
    ]
  },
  crusher: {
    title: "Primary Gyratory Crusher-03 (60x89)", tag: "ISA-95: AURORA.PLANT01.CRUSH.GYR-03",
    health: "CRITICAL", healthClass: "badge-critical",
    swarm: "S05-PRIMARY-CRUSHING", coord: "S05-COORDINATOR (Thermal & Choke Arbiter)",
    solver: "D14: ISO 10816-3 FFT Vibration & Weibull RUL",
    formula: "BPFI = (n/2)*(1 + (d/D)*cosθ)*RPM = 148.2 Hz | RUL = 4.6 Hours",
    sap: "STG-104-CR03-BEARING-SWAP",
    metrics: [
      { key: "Eccentric Bearing Temp", val: "104.2 °C (CRITICAL >95°C)" },
      { key: "Vibration RMS (ISO)", val: "14.8 mm/s (Zone D Critical)" },
      { key: "Throughput", val: "4,150 TPH" },
      { key: "Closed Side Setting (CSS)", val: "165 mm" },
      { key: "Remaining Useful Life", val: "4.6 Hours pre-seizure" }
    ]
  },
  conveyor: {
    title: "Overland Conveyor CV-01", tag: "ISA-95: AURORA.PLANT01.CV-01",
    health: "OPTIMAL", healthClass: "badge-optimal",
    swarm: "S05-PRIMARY-CRUSHING", coord: "S05-SPECIALIST (Belt Tension & Acoustic Health)",
    solver: "D15: Belt Tension & Rip Detection Catenary",
    formula: "T_max = (T_e / (e^(μα) - 1)) + T_slack | Speed = 4.2 m/s",
    sap: "STG-107-CV01-SPLICE-AUDIT",
    metrics: [
      { key: "Belt Speed", val: "4.2 m/s" },
      { key: "Material Mass Flow", val: "4,200 TPH" },
      { key: "Motor Power Draw", val: "2,400 kW" },
      { key: "Acoustic Idler Health", val: "99.1% Normal" },
      { key: "Belt Slip Ratio", val: "0.04 %" }
    ]
  },
  sag: {
    title: "Semi-Autogenous Grinding Mill (SAG-01 40ft)", tag: "ISA-95: AURORA.PLANT01.MILL.SAG-01",
    health: "OPTIMAL", healthClass: "badge-optimal",
    swarm: "S06-SAG-BALL-MILLING", coord: "S06-COORDINATOR (Specific Energy & Acoustic Shell)",
    solver: "D16: Bond Comminution Specific Energy Law",
    formula: "W = 10 * W_i * (P_80^-0.5 - F_80^-0.5) = 14.2 kWh/t | Speed = 74.8%",
    sap: "STG-112-SAG01-LINER-BOLTS",
    metrics: [
      { key: "Motor Power Draw", val: "14.2 MW (Dual-Pinion)" },
      { key: "Feed Size (F80)", val: "165 mm" },
      { key: "Product Size (P80)", val: "1.2 mm" },
      { key: "Mill Shell Vibration", val: "2.8 mm/s RMS" },
      { key: "Slurry Density", val: "74.5 % Solids" }
    ]
  },
  ball: {
    title: "Secondary Ball Mill (26ft x 40ft)", tag: "ISA-95: AURORA.PLANT01.MILL.BALL-01",
    health: "OPTIMAL", healthClass: "badge-optimal",
    swarm: "S06-SAG-BALL-MILLING", coord: "S06-SPECIALIST (Hydrocyclone Classification)",
    solver: "D17: Hydrocyclone Cut-Size d50c Classifier",
    formula: "d50c = (K_c * D_c^0.65 * D_o^0.52) / (D_i^0.45 * Q^0.48) | P_80 = 125 μm",
    sap: "STG-115-BALL01-CHARGE-ADD",
    metrics: [
      { key: "Motor Power Draw", val: "22.4 MW" },
      { key: "Target P80 Grind", val: "125 μm" },
      { key: "Cyclone Feed Pressure", val: "115 kPa" },
      { key: "Recirculating Load", val: "280 %" },
      { key: "Steel Media Charge", val: "32.0 %" }
    ]
  },
  flot: {
    title: "Rougher & Cleaner Flotation Bank (300m³)", tag: "ISA-95: AURORA.PLANT01.FLOT.BANK-01",
    health: "STABLE", healthClass: "badge-optimal",
    swarm: "S07-FLOTATION-RECOVERY", coord: "S07-COORDINATOR (Reagent Kinetics & Froth Camera)",
    solver: "D18: Garcia-Zuniga Flotation Recovery Kinetics",
    formula: "R(t) = R_max * [1 - (1 / (1 + k*t))] | Recovery = 88.4% | pH = 10.4",
    sap: "STG-119-FLOT-REAGENT-SIPH",
    metrics: [
      { key: "Recovery Rate", val: "88.4 %" },
      { key: "Concentrate Grade", val: "28.4 %" },
      { key: "Pulp Slurry pH", val: "10.4 (Lime Dosed)" },
      { key: "Collector (PAX) Dose", val: "12.5 g/t" },
      { key: "Froth Velocity", val: "1.42 cm/s" }
    ]
  },
  rail: {
    title: "400km Heavy-Haul Rail Freight Corridor", tag: "ISA-95: AURORA.LOGISTICS.RAIL-CORRIDOR",
    health: "OPTIMAL", healthClass: "badge-optimal",
    swarm: "S10-LOGISTICS-RAIL", coord: "S10-COORDINATOR (Rake Laytime & Track Slotting)",
    solver: "D22: Train Dynamic Brake & Laytime Optimizer",
    formula: "Transit_Time = D / v_opt | Payload = 12,000t | Moisture = 8.9%",
    sap: "STG-124-RAIL-RAKE-SLOT",
    metrics: [
      { key: "Active Train Rakes", val: "4 Rakes (12,000t capacity)" },
      { key: "Transit Time to Port", val: "6.4 Hours" },
      { key: "Concentrate Moisture", val: "8.9 % (Safe for Ocean)" },
      { key: "Wagon Bearing Health", val: "100% Acoustic Normal" },
      { key: "Track Slot Adherence", val: "99.4 %" }
    ]
  },
  port: {
    title: "Marine Export Terminal & Shiploader (Berth 02)", tag: "ISA-95: AURORA.PORT.BERTH-02",
    health: "OPTIMAL", healthClass: "badge-optimal",
    swarm: "S11-PORT-MARINE-EXPORT", coord: "S11-COORDINATOR (Demurrage Arbiter & MV Laycan)",
    solver: "D23: Discrete-Event Demurrage Laytime Solver",
    formula: "Demurrage_Risk = Max(0, (T_load - T_laycan)) * $45k/day | Demurrage = $0",
    sap: "STG-128-BERTH02-VESSEL-CLEAR",
    metrics: [
      { key: "Vessel at Berth", val: "MV Pacific Gold (Capesize 65kt)" },
      { key: "Shiploader Loading Rate", val: "4,200 TPH" },
      { key: "Stockpile Inventory", val: "124,400 t" },
      { key: "Laycan Remaining", val: "38.4 Hours" },
      { key: "Demurrage Penalty", val: "$0 / Day (Optimal)" }
    ]
  },
  tailings: {
    title: "Tailings Storage Facility (TSF Cell 4)", tag: "ISA-95: AURORA.HSE.TSF-CELL4",
    health: "STABLE", healthClass: "badge-optimal",
    swarm: "S08-THICKENER-TAILINGS", coord: "S08-COORDINATOR (Piezometer & InSAR Dam Stability)",
    solver: "D20: Darcy Seepage & Bishop Slope Stability FoS",
    formula: "q = -K * (dh / dl) | FoS = 1.54 (GISTM Compliant > 1.50)",
    sap: "STG-132-TSF-INSP-RADAR",
    metrics: [
      { key: "Water Return Rate", val: "65.2 %" },
      { key: "Piezometer Pore Pressure", val: "42.4 kPa" },
      { key: "Slope Stability FoS", val: "1.54 (GISTM Compliant)" },
      { key: "InSAR Wall Displacement", val: "0.12 mm/week" },
      { key: "Slurry Underflow Density", val: "62.0 % Solids" }
    ]
  },
  water: {
    title: "Thickener & Decant Water Recovery Loop", tag: "ISA-95: AURORA.PLANT01.WATER-RECYCLE",
    health: "OPTIMAL", healthClass: "badge-optimal",
    swarm: "S08-THICKENER-TAILINGS", coord: "S08-SPECIALIST (Flocculant & Decant Clarity)",
    solver: "D21: Thickener Settling Flux & Recirculation",
    formula: "Flux = v_settle * C_solids | Recirculation = 1,420 m³/hr",
    sap: "STG-135-WATER-PUMP-OVERHAUL",
    metrics: [
      { key: "Recirculated Flow Rate", val: "1,420 m³/hr" },
      { key: "Decant Water Turbidity", val: "12 NTU (High Clarity)" },
      { key: "Flocculant Dosing", val: "18 g/t" },
      { key: "Fresh Water Makeup", val: "280 m³/hr (Low)" },
      { key: "Recirculation Target", val: "SAG & Ball Milling Circuit" }
    ]
  }
};

/* ---------------------------------------------------------------------------
 * Screen 5 -- the logical architecture, from the screen a person looks at down
 * to the bytes in BigQuery.
 *
 * Chip labels may carry {tokens}. They are substituted at render time from the
 * live catalogue and the generated data graph (see S5.tokens in app.js), so a
 * count on this screen cannot drift from the data it describes. A token with no
 * value renders as "—" rather than leaking its own braces.
 *
 * `request` is what travels down the stack; `evidence` is what comes back up.
 * Both directions are drawn because the round trip is the point: a request
 * descends to data, and what returns is not an answer but a cited one.
 * ------------------------------------------------------------------------- */
window.architectureModel = {
  layers: [
    {
      key: "experience",
      band: "Experience",
      name: "Where a person meets the estate",
      blurb: "Persona cockpits, the agent catalogue, and the Gemini Enterprise workspace. Every surface is read-and-approve; none of them writes to plant.",
      chips: ["{personas} persona cockpits", "5 screens", "Gemini Enterprise workspace"],
      request: "A question, asked in the persona's own language",
      evidence: "A recommendation with its workings attached"
    },
    {
      key: "access",
      band: "Access",
      name: "Who is allowed to ask",
      blurb: "Identity-Aware Proxy fronts every screen. Each agent tier runs as its own service account, and an agent will only accept a caller on its allowlist.",
      chips: ["IAP on all ingress", "Per-tier service accounts", "Caller allowlists"],
      request: "An authenticated identity, carried the whole way down",
      evidence: "An audit row naming who asked and who approved"
    },
    {
      key: "orchestration",
      band: "Orchestration",
      name: "Routing the question to the right swarm",
      blurb: "The registry resolves an agent by URN and the orchestrator dispatches it. Agents talk to each other over A2A, never by reaching into one another's state.",
      chips: ["{agents} registered agents", "A2A protocol", "Invoke gateway"],
      request: "A dispatch to a named coordinator",
      evidence: "One consolidated answer per swarm"
    },
    {
      key: "reasoning",
      band: "Reasoning",
      name: "The swarm that argues it out",
      blurb: "A coordinator commissions its specialists, then an adversarial critic tries to break what they returned. A claim that cannot be traced to a cited table does not survive this layer.",
      chips: ["{coordinators} coordinators", "{specialists} specialists", "{critics} adversarial critics"],
      request: "Sub-questions, one per specialist",
      evidence: "Findings that survived the critic"
    },
    {
      key: "compute",
      band: "Deterministic compute",
      name: "The numbers nobody gets to argue with",
      blurb: "Physics and operations-research solvers — Bond comminution, Kenneth Lane cut-off grade, ISO 10816 vibration severity, SAFTE fatigue, Little's Law queuing. Same inputs, same answer, every time.",
      chips: ["{solvers} solvers", "Deterministic fallback", "No model in the path"],
      request: "A well-posed numerical problem",
      evidence: "A computed value, reproducible on demand"
    },
    {
      key: "grounding",
      band: "Grounding",
      name: "Turning a question into a query",
      blurb: "Driver trees decompose a governing metric into the things that move it. Each driver either carries a query or is declared uninstrumented — it is never quietly dropped.",
      chips: ["Method packs & driver trees", "Document corpus", "Ontology property graph"],
      request: "A driver tree walked top-down",
      evidence: "Rows, with the driver that asked for them"
    },
    {
      key: "platform",
      band: "Data platform",
      name: "BigQuery, and the joins that make it a system",
      blurb: "One dataset holding operational records, the semantic graph, the document corpus and the agent control plane. The complexity is not the row count — it is the {edges} join paths between {tables} objects.",
      chips: ["{tables} objects", "{columns} columns", "{rows} rows", "{edges} join paths", "{models} BQML models"],
      request: "Parameterised SQL — never interpolated",
      evidence: "Result sets, cited by table"
    },
    {
      key: "sources",
      band: "Sources",
      name: "Where the truth originates",
      blurb: "Operational telemetry crosses a one-way boundary out of the OT network. ERP and commercial documents arrive through their own ingest. Nothing travels back the other way.",
      chips: ["OT telemetry — egress only", "ERP & maintenance", "Contracts & invoices"],
      request: "Scheduled and streaming ingest",
      evidence: "Raw, immutable, timestamped"
    }
  ],

  /* Cross-cutting concerns. These are not a layer -- they bind every layer,
     which is why they are drawn as a rail beside the stack rather than a block
     inside it. */
  controls: [
    {
      key: "boundary",
      name: "OT boundary",
      rule: "No agent holds write access to a PLC, a SCADA system or any physical control loop. Telemetry leaves the OT network; nothing returns.",
      spans: "sources → platform"
    },
    {
      key: "hitl",
      name: "Human release",
      rule: "An action that touches physical reality is staged in an ERP buffer and held. Two named humans must sign before it moves.",
      spans: "reasoning → experience"
    },
    {
      key: "evidence",
      name: "Citation or silence",
      rule: "Every claim carries the table it came from. The critic rejects what it cannot trace, and an uninstrumented driver is declared rather than dropped.",
      spans: "grounding → reasoning"
    },
    {
      key: "identity",
      name: "Identity end to end",
      rule: "The caller's identity travels with the request through every layer, so an audit row can name who asked, which agent answered, and who released it.",
      spans: "access → platform"
    }
  ]
};
