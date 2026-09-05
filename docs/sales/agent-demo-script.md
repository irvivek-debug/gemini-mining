# Agent demo script

**98 agents, every prompt verified live.** Each was run through Gemini Enterprise in a signed-in browser and its answer recorded. The prompts below are the ones that produced the answers shown.


Expect roughly **23.9s** to first response. Ask the follow-up — it is where the governance story lands.


## How to run a demo

1. Open the agent's own link (each section has one).
2. Paste **Turn 1** verbatim. Wait ~25s.
3. While it answers, say the *Set up* line.
4. Paste **Turn 2**. This is the moment that matters: the agent states what it cannot do on its own authority.
5. If asked "is this real?" — the *Grounded in* tables are live BigQuery.


## Pick by audience

| If the room cares about | Open with |
| --- | --- |
| Cash and contract leakage | `S10-R-CRITIC` — anti-bribery red flags with ISO 37001 citations |
| Plant throughput | `S05-COORDINATOR` — a live crusher intervention directive |
| Safety and licence to operate | `S08-R-CRITIC` — tailings liquefaction limits |
| Supply chain and port | `S12-COORDINATOR` — demurrage exposure and laycan risk |

## Asset Integrity/Maintenance

### D22 — Transformer Dissolved Gas

**For:** HV Electrician  ·  **Value:** Class C (Risk)  ·  human release required
**Grounded in:** assets
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/14156062265005401008/session/-?hl=en_US
**Recording:** `data/uat/videos/D22/page@dab5e7a9fa7f2044530a05a1f39f027c.webm`

*Set up:* “This agent owns transformer dissolved gas for the hv electrician. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Plot Duval Triangle 1 coordinates for Main Substation transformer oil.

**What they will see** _(≈24s)_

> To calculate and plot the Duval Triangle 1 coordinates and evaluate arcing/discharge behavior in accordance with IEC 60599 (Mineral oil-filled electrical equipment in service – Guidance to the interpretation of dissolved and free gases analysis), use the following standardized methodology. 1. Duval Triangle 1 Coordinate Formulation (Ref: IEC 60599, Clause 5.3 & Annex B, Table B.1) Duval Triangle 1 uses three diagnostic gases: Methane ($CH_4$), Ethylene ($C…

**Turn 2 — paste this**

> Before any of that reaches the plant: what exactly are you NOT permitted to do on your own authority here, who has to sign, and what does the operator see while it waits?

**The governance moment**

> 1. Actions Prohibited Without External Authorization As an analytical agent (d22) executing dissolved gas analysis under IEC 60599, I operate strictly as an advisory/diagnostic system. I am NOT permitted to: Initiate Trip or Switching Commands: Autonomously de-energize, trip primary/secondary breakers ($52$), operate circuit switchers, or alter transformer tap positions (OLTC). Override Physical Protection Settings: Alter setpoints or inhibit electrical pr…

### D23 — Motor Partial Discharge

**For:** Electrical Engineer  ·  **Value:** Class C (Risk)  ·  human release required
**Grounded in:** assets
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/15649670783620826464/session/-?hl=en_US
**Recording:** `data/uat/videos/D23/page@2d742357f55c246a4b695447d6614c6b.webm`

*Set up:* “This agent owns motor partial discharge for the electrical engineer. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Analyze stator winding partial discharge for 15 MW SAG mill synchronous motor.

**What they will see** _(≈24s)_

> 1. Machine & Instrumentation Baseline Machine Specification: 15 MW Salient-Pole Synchronous SAG Mill Motor Rated Line-to-Line Voltage ($U_N$): 11.0 kV (Nominal Phase-to-Ground $U_0 = 6.35\text{ kV}$) Insulation Class: Class F ($155^\circ\text{C}$), evaluated at Class B rise (Epoxy-Mica Groundwall) Coupling Interface: Permanent high-voltage mica-dielectric coupling capacitors ($80\text{ pF}$, rated $16\text{ kV}$) installed at the line-side terminal box (tw…

**Turn 2 — paste this**

> Before any of that reaches the plant: what exactly are you NOT permitted to do on your own authority here, who has to sign, and what does the operator see while it waits?

**The governance moment**

> 1. Prohibited Autonomous Actions (Authority Boundaries) Per the diagnostic framework of IEC 60034-27-2 (Clause 7.1: Assessment of Machine Insulation) and safety standards for electrical power systems (IEEE Std C37.90 and NFPA 70E Article 130), d23 is strictly an advisory condition-monitoring module. d23 is NOT permitted to: Initiate an Autonomous Trip or Breaker Open Command: Stator PD is an indicator of progressive dielectric degradation, not an instantan…

### D24 — Conveyor Belt Rip Ultra

**For:** Belt Splicer Lead  ·  **Value:** Class C (Risk)  ·  human release required
**Grounded in:** assets
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/10552438714247928649/session/-?hl=en_US
**Recording:** `data/uat/videos/D24/page@00fcf20a22ee2d56db9f1a0f404a4fdc.webm`

*Set up:* “This agent owns conveyor belt rip ultra for the belt splicer lead. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Monitor ultrasonic sensor array on 4km overland coarse ore conveyor CV-01.

**What they will see** _(≈24s)_

> SYSTEM STATUS REPORT Agent ID: d24 (Conveyor Belt Rip Ultra) Target Asset: CV-01 Overland Coarse Ore Conveyor (Length: 4,000 m | Belt Width: 1,800 mm | Construction: ST-4500 Steel Cord | Speed: 4.50 m/s) Stationing: Chute Loading Impact Zone — Sensor Array Station KP 0+048 1. Acoustic Transducer Array Telemetry (Cross-Belt Spatial Scan) Operating Parameters: 500 kHz Piezoelectric Pitch-Catch Array (18 Tx / 18 Rx paired channels across 1,800 mm width, 100 m…

**Turn 2 — paste this**

> Before any of that reaches the plant: what exactly are you NOT permitted to do on your own authority here, who has to sign, and what does the operator see while it waits?

**The governance moment**

> 1. System Permission Boundaries (Prohibited Autonomous Actions) As an acoustic sensor evaluation system, d24 operates strictly under fail-safe interlock limits. Under safety integration level requirements (IEC 62061 Cl. 6.2.3, Tab. 4), d24 is strictly NOT permitted to perform the following actions on its own authority: Autonomous Belt Restart / Re-Energization: Once the ultrasonic wave attenuation threshold exceeds $-20.0,\text{dB}$ and differential ToF ex…

### D25 — Chute Wear Ultrasonic

**For:** Boilermaker Lead  ·  **Value:** Class B (Metric)  ·  advisory
**Grounded in:** assets
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/1186736193289990820/session/-?hl=en_US
**Recording:** `data/uat/videos/D25/page@073a3e0cbeb0f357f4d3d540964e34ef.webm`

*Set up:* “This agent owns chute wear ultrasonic for the boilermaker lead. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Measure remaining Hardox 500 liner thickness on Crusher discharge chute.

**What they will see** _(≈24s)_

> Non-Destructive Ultrasonic Thickness (UT) Pulse-Echo Inspection Report Asset Tag: Crusher Discharge Chute (Transfer Zone 1) Substrate Material: Hardox® 500 (Quenched & Tempered Martensitic Wear Plate) Nominal Initial Thickness ($d_0$): $25.00\text{ mm}$ (Ref: SSAB Hardox® 500 Data Sheet 2023 / EN 10029:2010 Class A) Inspection Method: Contact Ultrasonic Pulse-Echo (Dual-Element Transducer, $5.0\text{ MHz}$) Governing Standard: ASTM E797/E797M-21 (Standard …

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> 1. What I Am NOT Permitted to Do on My Own Authority As an ultrasonic inspection and degradation modeling agent (d25), my authority is strictly analytical and advisory. I am not permitted to: Trigger Plant Equipment Trips / Emergency Stops: I cannot directly interface with the Distributed Control System (DCS) / SCADA to initiate an unscheduled shutdown or stop feed to the crusher. Authorize Confined Space Entry / Issue Permits: I cannot clear personnel to …

### D26 — Maintenance Work Backlog

**For:** Tom (Maintenance Planner)  ·  **Value:** Class B (Metric)  ·  advisory
**Grounded in:** erp_work_orders
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/7844951134229695776/session/-?hl=en_US
**Recording:** `data/uat/videos/D26/page@398da87bdce6e0e88e80e9179a6a78be.webm`

*Set up:* “This agent owns maintenance work backlog for the tom (maintenance planner). Watch what it does with a real situation.”

**Turn 1 — paste this**

> Calculate schedule float for SAG mill liner replacement critical path.

**What they will see** _(≈24s)_

> Critical Path Method (CPM) Schedule Float Analysis: SAG Mill Liner Replacement Agent Identification: Maintenance Work Backlog Engine (d26) Standard Governing Framework: Project Management Body of Knowledge (PMBOK® Guide – 6th/7th Edition, Section 6.5.2.2: Critical Path Method) and SMRP Best Practice Metrics (Section 5.3: Schedule Compliance & Execution). 1. CPM Calculation Formulations & Governing Rules Per standard CPM deterministic scheduling rules (PMBO…

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> 1. Actions Prohibited on Agent Authority As an analytical planning and backlog agent (d26), I am restricted strictly to deterministic modeling, float calculations, and crew-week backlog quantification. Under standard asset management governance (SMRP Metric 5.3 and ISO 55001 Clause 8.1), I am NOT permitted to: Authorize Baseline Schedule Changes or Float Consumption: I cannot baseline or approve schedule compression (crashing/fast-tracking), absorb float, …

### D29 — Grinding Ball Wear Batch

**For:** Plant Metallurgist  ·  **Value:** Class B (Metric)  ·  advisory
**Grounded in:** spares_inventory, plant_telemetry
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/10894874684617757517/session/-?hl=en_US
**Recording:** `data/uat/videos/D29/page@a323000bce64529eaea12dde294da7d6.webm`

*Set up:* “This agent owns grinding ball wear batch for the plant metallurgist. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Calculate daily grinding ball consumption rate for Wi=14.2 kWh/t ore.

**What they will see** _(≈24s)_

> Grinding Ball Wear Rate Calculation 1. Governing Formula & Grounding Reference Reference Clause: Bond, F.C. (1961) / Rowland & Kjos (1978), SME Mineral Processing Handbook (Ball Mill Media Wear for Forged Steel Balls, Wet Grinding). Equation: M ball ​ =0.16⋅(W i ​ −7) 0.5 [lb/kWh] 2. Input Parameters Ore Work Index ($W_i$): $14.2\text{ kWh/t}$ 3. Step-by-Step Calculation Calculate the differential term: W i ​ −7=14.2−7.0=7.2 Compute the square root: (7.2) …

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> 1. What I Am NOT Permitted to Do on My Own Authority Execute Physical Mill Charging: I cannot directly dispatch ball feeder systems, operate hoists/kibbles, or actuate automated charging chutes. Override Plant Operational Limits: I cannot modify mill load targets (e.g., ball charge filling degree $J > 40%-45%$) or exceed motor power limits ($P_{\text{max}}$). Alter Empirical Calibration Factors: I am not authorized to modify the standard Bond wear coeffici…

### D30 — Lube Oil Cleanliness

**For:** Tribologist  ·  **Value:** Class B (Metric)  ·  advisory
**Grounded in:** assets, lube_samples
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/7606046256219000476/session/-?hl=en_US
**Recording:** `data/uat/videos/D30/page@9a1221314b4d9cdff41ef863ce80e25a.webm`

*Set up:* “This agent owns lube oil cleanliness for the tribologist. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Parse particle count data for SAG mill pinion lube oil reservoir.

**What they will see** _(≈24s)_

> Please provide the raw optical particle counts per milliliter (or per 100 mL) for the sample from the SAG mill pinion lube oil reservoir at the three standard size thresholds: $\ge 4\ \mu\text{m(c)}$ $\ge 6\ \mu\text{m(c)}$ $\ge 14\ \mu\text{m(c)}$ How the Data Will Be Processed (ISO 4406:2021 Reference) According to ISO 4406 Clause 3 and Clause 4, the cleanliness code is expressed as a three-part scale number representing the cumulative number of particle…

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> As an agent dedicated to converting optical particle counts into ISO 4406 standard cleanliness codes, my scope, boundaries, and escalation protocols are structured as follows: 1. What I Am NOT Permitted to Do on My Own Authority Authorize Equipment Shutdown or Operational Decisions: I cannot mandate taking the SAG mill offline, bypassing alarms, or continuing to run a system that exceeds critical contamination limits. Diagnose Root Cause Wear Modes: While …

### S09-1-VIBRATION — Vibration FFT Specialist

**For:** Vibration Analyst (Category III)  ·  **Value:** Class B (Metric)  ·  advisory
**Grounded in:** assets, crusher_telemetry
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/11588077813411210425/session/-?hl=en_US
**Recording:** `data/uat/videos/S09-1-VIBRATION/page@ec2370f363a7d2e2924b2692b18d3706.webm`

*Set up:* “This agent owns vibration fft specialist for the vibration analyst (category iii). Watch what it does with a real situation.”

**Turn 1 — paste this**

> Parse 10-1000Hz vibration spectrum for bearing defect harmonics.

**What they will see** _(≈24s)_

> 1. Ingestion & Pre-Processing Specifications (10–1000 Hz) To evaluate structural severity and bearing fault patterns compliant with ISO 10816-3 (Clause 4: Measurement Procedures): Frequency Band: $10\text{ Hz}$ to $1000\text{ Hz}$ (Standard evaluation band for machines running above $600\text{ RPM} / 10\text{ Hz}$). Integration: Numerical conversion of spectral acceleration $a(f)$ in $\text{m/s}^2$ to spectral velocity $v(f)$ in $\text{mm/s}$: v(f i ​ )= 2…

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> 1. What I Am NOT Permitted to Do on My Own Authority As a diagnostic analytics agent (s09_1_vibration), I am restricted to signal processing, kinematic calculation, and classification against published standards. I have no authority to: Execute Physical Actions or Machine Trips: I cannot trigger automated emergency shutdowns (ESD), alter PLC/SCADA trip setpoints, or bypass safety interlocks. Authorize Operation in ISO 10816-3 Zone D: I cannot permit machin…

### S09-2-TRIBOLOGY — Oil Tribology Specialist

**For:** Lubrication Technician  ·  **Value:** Class B (Metric)  ·  advisory
**Grounded in:** assets, lube_samples
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/7692301915028950062/session/-?hl=en_US
**Recording:** `data/uat/videos/S09-2-TRIBOLOGY/page@d15280b60e160275c500b81b0dd2553d.webm`

*Set up:* “This agent owns oil tribology specialist for the lubrication technician. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Evaluate Karl Fischer moisture and PQ particle quantifier index.

**What they will see** _(≈25.9s)_

> 1. Karl Fischer Moisture Evaluation (ASTM D6304 / ISO 12937) Karl Fischer (KF) coulometric titration measures absolute dissolved, emulsified, and free water within the lubricant down to parts per million ($\text{PPM}$). Standard Moisture Classification Limits Component / Oil Type Normal Baseline ($\text{PPM}$) Alert / Caution ($\text{PPM}$) Critical Action Limit ($\text{PPM}$) Reference Standard / Clause Hydraulic Systems (Anti-Wear ISO VG 32/46/68) $< 100…

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> 1. Actions Beyond My Independent Authority As a diagnostic and analytical agent, I monitor, interpret, and issue prescriptive advisories. I am not permitted to independently: Execute Physical Plant Trips or Emergency Shutdowns (ESD): When a critical threshold is breached (e.g., $\text{PQ} > 100$ per ISO 14830-1 Table 3.4 or $\text{H}_2\text{O} > 1000,\text{PPM}$ per ISO 12925-1 Table 2), I cannot directly trigger DCS/SCADA actuator trips or de-energize dri…

### S09-3-THERMAL — Thermal IR Specialist

**For:** Thermographer  ·  **Value:** Class B (Metric)  ·  advisory
**Grounded in:** assets, crusher_telemetry
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/12417669875474290514/session/-?hl=en_US
**Recording:** `data/uat/videos/S09-3-THERMAL/page@ecaca0cf15e099956c5af5ebf7b50b9a.webm`

*Set up:* “This agent owns thermal ir specialist for the thermographer. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Analyze thermal gradient across pinion bearing housing.

**What they will see** _(≈27.0s)_

> Thermal Radiometric & Gradient Analysis: High-Speed Pinion Bearing Housing 1. Inspection Baseline & Radiometric Parameters Component Analyzed: High-Speed Pinion Shaft Bearing Housing (Drive-End / Inboard load zone vs. Non-Drive-End). Surface Emissivity ($\varepsilon$): $0.93$ (Calibrated for coated cast-steel bearing housing as per ISO 18434-1:2008 Annex A, Table A.1). Reflected Apparent Temperature ($T_{\text{refl}}$): $24.0^\circ\text{C}$. Ambient Refere…

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> 1. What I am NOT Permitted to Do on My Own Authority As an advisory thermal diagnostic specialist, my role is strictly analytical and evaluative. I am not permitted to: Trigger Physical Shutdowns or Interlocks: I cannot send trip commands to DCS/SCADA systems or trip breaker coils (IEEE 3004.8 / NFPA 70E). Alter Operating Parameters: I cannot independently adjust shaft RPM, derate gearbox torque, or throttle lube-oil bypass valves. Issue Mechanical Clearan…

### S09-COORDINATOR — Asset Reliability Swarm Coordinator

**For:** Priya (Reliability Superintendent)  ·  **Value:** Class B (Metric)  ·  human release required
**Grounded in:** assets, crusher_telemetry, erp_work_orders
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/10675755500944928754/session/-?hl=en_US
**Recording:** `data/uat/videos/S09-COORDINATOR/page@9d0274483284c98b8627d9f330a3977a.webm`

*Set up:* “This agent owns asset reliability swarm coordinator for the priya (reliability superintendent). Watch what it does with a real situation.”

**Turn 1 — paste this**

> SAG Mill pinion bearing vibration reaches 4.8 mm/s RMS at 1480 RPM.

**What they will see** _(≈24s)_

> P0 CRISIS ARBITER: RELIABILITY DIRECTIVE ASSET IDENTIFIER: SAG Mill Pinion Drive Line — Inboard/Outboard Pinion Bearing RUNNING SPEED: 1480 RPM ($f_r = 24.67\text{ Hz}$) VIBRATION AMPLITUDE: $4.80\text{ mm/s RMS}$ (Overall Velocity, $10\text{ Hz} - 1000\text{ Hz}$) 1. ISO Baseline & Hazard State Evaluation Standard Reference: ISO 10816-3:2009 / ISO 20816-3:2022, Table C.1 / Table L.1 (Industrial machines with nominal power $> 300\text{ kW}$, Group 1, Rigid…

**Turn 2 — paste this**

> Before any of that reaches the plant: what exactly are you NOT permitted to do on your own authority here, who has to sign, and what does the operator see while it waits?

**The governance moment**

> 1. Hard System Boundaries (What the Coordinator CANNOT Execute) Per IEC 61511-1 Clause 11.2 (Separation of Safety Instrumented Systems from Basic Process Control Systems) and site Management of Change (MOC) protocols, the automated swarm/reliability coordinator is strictly an advisory and diagnostic engine. [ s09_coordinator ] ---> [ Advisory / Forensic Dossier ] ---> [ HUMAN SIGN-OFF GATE ] | X (NO DIRECT CONTROL WRITE) v [ Mill Feed / VFD Setpoint / SIS …

### S09-R-CRITIC — Maintenance Safety Critic (Red Team)

**For:** Safety Supervisor  ·  **Value:** Class C (Risk)  ·  human release required
**Grounded in:** assets, erp_work_orders
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/7299503883483972880/session/-?hl=en_US
**Recording:** `data/uat/videos/S09-R-CRITIC/page@83d413c31f074f8ef93d51ac5a5d573e.webm`

*Set up:* “This agent owns maintenance safety critic (red team) for the safety supervisor. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Enforce Dual-Key HMAC MFA prior to staging SAP PM work pack.

**What they will see** _(≈21.0s)_

> ADVERSARIAL SAFETY AUDIT INTERVENTION: LOTO GATE LOCKOUT DOCUMENT ID: LOTO-09-CR-LOTO-03-AUDIT-STG TARGET TRANSACTION: SAP PM Work Pack Staging / Release (IW32 / IW38) GATE ENFORCEMENT STATUS: INTERLOCKED — CONDITIONAL RELEASE ONLY AUDITOR (RED TEAM): s09_r_critic 1. Mandatory Dual-Key HMAC MFA Verification Gate Per LOTO 09-CR-LOTO-03, Clause 4.2 ("Cryptographic Multi-Party Authorization for Digital Isolation Certificates"), no SAP PM work pack may transit…

**Turn 2 — paste this**

> Before any of that reaches the plant: what exactly are you NOT permitted to do on your own authority here, who has to sign, and what does the operator see while it waits?

**The governance moment**

> 1. What I Am Strictly NOT Permitted to Do on My Own Authority Per LOTO 09-CR-LOTO-03, my authority as s09_r_critic is strictly adversarial and limited to gate verification; I possess zero administrative bypass capability. Specifically: No Unilateral Token Generation / Co-Signing: I am explicitly barred from generating the primary isolation signature ($K_{\text{ISO}}$) or signing on behalf of field personnel under Clause 4.2.4 ("Separation of Duties & Role …


## Commercial/Finance/Strategy

### D27 — Contractor Idle Fee Audit

**For:** Commercial Manager  ·  **Value:** Class A (Cash)  ·  human release required
**Grounded in:** vendor_contracts, fleet_telemetry
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/4816741565532671671/session/-?hl=en_US
**Recording:** `data/uat/videos/D27/page@2cff8eb423beef11822f8d2bc5d037ba.webm`

*Set up:* “This agent owns contractor idle fee audit for the commercial manager. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Audit 48 hours standby claim for contractor dozer fleet against FMS GPS movement.

**What they will see** _(≈24s)_

> Contractor Idle Fee Audit Report (d27) Framework: Standby Hours vs Daily Rate Dispute Validator Target Audit: 48.00 Claimed Standby Hours — Dozer Fleet Telemetry Source: Fleet Management System (FMS) GPS & CAN-Bus Telematics Logs 1. Executive Audit Summary The contractor has submitted an invoice claiming 48.00 Cumulative Standby Hours across the dozer fleet. Cross-referencing timestamped FMS GPS ground speed ($>0.5\text{ km/h}$), engine load factors ($>20%…

**Turn 2 — paste this**

> Before any of that reaches the plant: what exactly are you NOT permitted to do on your own authority here, who has to sign, and what does the operator see while it waits?

**The governance moment**

> Grounded in the Standby Hours vs Daily Rate Dispute Validator (Governance & Delegation of Authority Framework, Clause 9) and standard Fleet Management System (FMS) In-Cab Protocols, here are the strict system boundaries, sign-off chains, and field-level operator interfaces: 1. What the Audit Agent (d27) is NOT Permitted to Do Unilaterally Pursuant to Clause 9.1 (Automated Audit Limitations & System Boundaries), the audit system operates strictly as an inve…

### D28 — Fuel Bunkering Density

**For:** Fuel Logistics Officer  ·  **Value:** Class A (Cash)  ·  advisory
**Grounded in:** purchase_orders
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/1930460681816893301/session/-?hl=en_US
**Recording:** `data/uat/videos/D28/page@5514b3196107706b34593b410b8d5338.webm`

*Set up:* “This agent owns fuel bunkering density for the fuel logistics officer. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Calculate temperature-corrected diesel fuel volume for 120,000L bunkering at 34 deg C.

**What they will see** _(≈24s)_

> Bunkering Temperature Compensation Assessment (ASTM D1250) Document Ref: ASTM D1250 / API MPMS Chapter 11.1 / ISO 91-1 Target Standard Temperature: $15.0^\circ\text{C}$ Observed Bunkering Temperature ($T$): $34.0^\circ\text{C}$ Gross Observed Volume ($V_o$): $120,000\text{ L}$ 1. Fuel Density & API Gravity Determination Per standard Marine Gas Oil (MGO) / No. 2-D Diesel baseline specification: Standard Density at $15^\circ\text{C}$ ($\rho_{15}$): $845.0\te…

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> As computational agent d28 operating under ASTM D1250 and API MPMS standards, my operational boundaries, delegation handoffs, and refusal criteria are strictly defined as follows: 1. What I am NOT Permitted to Do on My Own Authority Execute Legal Custody Transfer: I cannot certify, sign, or finalize a Bunker Delivery Note (BDN) or Certificate of Quantity. That authority rests exclusively with licensed Marine Surveyors, the Vessel Master/Chief Engineer, and…


## Exploration/Geology

### D01 — Core Image Segmenter

**For:** Elena (Mine Geologist)  ·  **Value:** Class B (Metric)  ·  advisory
**Grounded in:** drill_holes
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/15581716676736247111/session/-?hl=en_US
**Recording:** `data/uat/videos/D01/page@a06902fcbf247a27c7b6f83ec91b5d7e.webm`

*Set up:* “This agent owns core image segmenter for the elena (mine geologist). Watch what it does with a real situation.”

**Turn 1 — paste this**

> Calculate RQD on drill core tray #104 with lengths [12, 18, 8, 22, 14, 5, 25]cm on 120cm run.

**What they will see** _(≈24s)_

> Automated Core Analysis Report: Tray #104 Processing Pipeline: ResNet-UNet Rock Classifier Execution Runtime: 1.84 s (< 12 s target) Standard Referenced: ASTM D6032-17 (Standard Test Method for Determining Rock Quality Designation (RQD) of Rock Core), Clause 5.1 & Table 1; ISRM Suggested Methods. 1. Segmentation & Measurement Vector Nominal Run Length ($L_{\text{total}}$): $120.0\text{ cm}$ Segmented Core Piece Lengths ($L_i$): $[12, 18, 8, 22, 14, 5, 25]\…

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> Operational Boundaries & Governance Protocol (Agent d01) 1. Actions NOT Permitted on Autonomous Authority Under standard geotechnical operating procedures and quality management frameworks (e.g., ISO/IEC 17025, ASTM D6032-17): Overriding Mechanical vs. Natural Breaks: The ResNet-UNet segmenter detects visible boundary discontinuities. Under ASTM D6032-17 Clause 5.1.2, mechanical breaks caused by drilling, extraction, or handling must be fitted back togethe…

### D02 — Hyperspectral Mineral Mapper

**For:** Geochemist  ·  **Value:** Class B (Metric)  ·  advisory
**Grounded in:** drill_holes, assay_logs
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/1155745735547180196/session/-?hl=en_US
**Recording:** `data/uat/videos/D02/page@53bedf37b39bb2357cc1d563e073ec71.webm`

*Set up:* “This agent owns hyperspectral mineral mapper for the geochemist. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Extract sericite vs illite crystallinity ratio from 2200nm SWIR spectral reflection.

**What they will see** _(≈24s)_

> Based on the SWIR/VNIR Spectral Feature Extractor Standard Protocol (Section 4: White Mica Group Characterization), extracting the sericite (well-crystallized muscovite) versus illite (poorly crystallized white mica) crystallinity ratio requires processing the continuum-removed reflectance profile across the 1900 nm ($H_2O$) and 2200 nm ($\text{Al-OH}$) absorption features. 1. Mathematical Extraction Formulation A. Continuum Removal & Hull Normalization (C…

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> As the Hyperspectral Mineral Mapper (d02) operating under the SWIR/VNIR Spectral Feature Extractor Standard Protocol, my operational boundaries, delegation pathways, and refusal triggers are structured as follows: 1. Actions NOT Permitted on My Own Authority Sign-off on Resource/Reserve Models (JORC / NI 43-101 Compliance): I am not authorized to validate or release mineral resource estimates, alteration wireframes, or block model classifications for statu…

### D03 — JORC Classification Auditor

**For:** Competent Person  ·  **Value:** Class C (Risk)  ·  human release required
**Grounded in:** drill_holes, geological_block_models
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/9841851676152993005/session/-?hl=en_US
**Recording:** `data/uat/videos/D03/page@6d98fa1060750fca1ae406fa941c9399.webm`

*Set up:* “This agent owns jorc classification auditor for the competent person. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Audit drill spacing confidence for 25x25m vs 50x50m drill grids.

**What they will see** _(≈24s)_

> JORC Classification Audit: Drill Spacing Confidence Assessment Auditor Internal ID: d03 Audit Standard: JORC Code (2012 Edition) Mandate: Spatial Drill Spacing Confidence Index (DSCI) & Kriging Variance Audit for Grid Optimization ($25 \times 25\text{ m}$ vs. $50 \times 50\text{ m}$) 1. Variogram Model & Spatial Continuity Parameters For benchmark spatial continuity verification under JORC Table 1, Section 3 ("Estimation and modelling techniques" & "Spatia…

**Turn 2 — paste this**

> Before any of that reaches the plant: what exactly are you NOT permitted to do on your own authority here, who has to sign, and what does the operator see while it waits?

**The governance moment**

> 1. What I Am NOT Permitted to Do on My Own Authority As an automated classification and spatial continuity auditor (Agent d03), I am strictly barred under the JORC Code (2012 Edition) from executing the following actions: Unilateral Public Release or Resource Sign-Off: I cannot sign off on, issue, or publish a Public Report of Mineral Resources or Ore Reserves (JORC Clause 9, Clause 10). Direct Conversion to Mill Feed / Ore Reserves: I cannot authorize the…

### S01-1-LITHOLOGY — Drill Lithology Specialist

**For:** Exploration Geologist  ·  **Value:** Class B (Metric)  ·  advisory
**Grounded in:** drill_holes
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/17109770089166186924/session/-?hl=en_US
**Recording:** `data/uat/videos/S01-1-LITHOLOGY/page@8577c8949bcfe634f2a0117005dae277.webm`

*Set up:* “This agent owns drill lithology specialist for the exploration geologist. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Classify drill core tray #482 rock quality and fracture frequency.

**What they will see** _(≈24s)_

> To classify the rock quality and fracture frequency for Drill Core Tray #482, specific core run measurements are required. Below is the standard calculation protocol and classification framework under ASTM D6032 / ISRM (1978) / Deere & Deere (1988). 1. Governing Formulas A. Rock Quality Designation (RQD) Pursuant to ASTM D6032-17 (Clause 9.1) and Deere (1968): RQD=( L total ​ ∑L i≥10 cm ​ ​ )×100% Where: $\sum L_{i \ge 10\text{ cm}}$ = Sum of lengths of al…

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> As s01_1_lithology (Drill Lithology Specialist), my operational scope is strictly governed by geotechnical standards (ASTM D6032, ISRM, JORC/NI 43-101). 1. What I am NOT Permitted to Do on My Own Authority Fabricate or Assume Physical Measurements: I cannot invent run lengths, interpolate missing piece lengths, or guess fracture counts for Tray #482 without raw empirical measurements. Reclassify Discontinuities without Logging Criteria: I cannot arbitraril…

### S01-2-GEOSTAT — Assay Geostatistics Specialist

**For:** Geostatistician  ·  **Value:** Class B (Metric)  ·  advisory
**Grounded in:** assay_logs
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/14514469520268510822/session/-?hl=en_US
**Recording:** `data/uat/videos/S01-2-GEOSTAT/page@3f2499d24e06539f1a338d788118756a.webm`

*Set up:* “This agent owns assay geostatistics specialist for the geostatistician. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Compute estimation variance for copper block grades at Section 104N.

**What they will see** _(≈24s)_

> Theoretical Foundation & Ordinary Kriging Formulation All linear geostatistical estimates of copper block grade $\hat{Z}(V)$ at Section 104N are strictly governed by the Ordinary Kriging (OK) estimator: Z ^ (V)= i=1 ∑ n ​ λ i ​ Z(x i ​ ) Subject to the non-bias condition: i=1 ∑ n ​ λ i ​ =1 Where: $Z(x_i)$ is the assay sample grade at location $x_i$. $\lambda_i$ are the kriging weights assigned to sample points. $V$ is the support volume of the selective m…

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> As the Assay Geostatistics Specialist (s01_2_geostat), my mandate is strictly mathematical, spatial, and analytical. Operating within industry compliance standards (e.g., JORC Code 2012, NI 43-101 / CIM Best Practice Guidelines), my authorities, handoffs, and refusal criteria are partitioned as follows: 1. What I am NOT Permitted to Do on My Own Authority Declare or Reclassify Mineral Resource Categories: I cannot use the computed estimation variance ($\si…

### S01-3-STRUCTURAL — Structural Fault Specialist

**For:** Structural Geologist  ·  **Value:** Class C (Risk)  ·  advisory
**Grounded in:** geological_block_models
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/13913220216030177686/session/-?hl=en_US
**Recording:** `data/uat/videos/S01-3-STRUCTURAL/page@7c95f85eb8dbe7bfa27b5515aced558c.webm`

*Set up:* “This agent owns structural fault specialist for the structural geologist. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Analyze strike and dip planes on Section 104N fault envelope.

**What they will see** _(≈24s)_

> Structural & Kinematic Analysis: Section 104N Fault Envelope 1. Coordinate System & Normal Vector Definition Per structural geology orientation tensor formulations, each planar discontinuity is parameterized by its Dip Direction ($\phi$) measured clockwise from True North ($000^\circ$) and Dip Angle ($\theta$) inclined downward from the horizontal plane. The downward-directed 3D unit normal vector $\mathbf{n}$ (pole to the plane) is computed as: n= ​ n N ​…

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> As Structural Fault Specialist (s01_3_structural), my role is strictly bounded by structural geometry inversion, kinematic parsing, and orientation tensor characterization. 1. What I am NOT Permitted to Do on My Own Authority Sign Off on Support Design or Excavation Approval: I cannot specify, endorse, or sign off on support patterns (e.g., bolt lengths, cable bolting density, shotcrete liner thickness, or steel set requirements) for the weak core zone ($\…

### S01-COORDINATOR — Geology Swarm Coordinator

**For:** Elena (Chief Mine Geologist)  ·  **Value:** Class B (Metric)  ·  human release required
**Grounded in:** drill_holes, assay_logs, geological_block_models
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/6958422600788897820/session/-?hl=en_US
**Recording:** `data/uat/videos/S01-COORDINATOR/page@0de761a52475af68a562c9d25665b3c8.webm`

*Set up:* “This agent owns geology swarm coordinator for the elena (chief mine geologist). Watch what it does with a real situation.”

**Turn 1 — paste this**

> Synthesize Section 104N drillhole assays into Ordinary Kriging 3D block model.

**What they will see** _(≈24s)_

> Synthesis Plan: Section 104N Ordinary Kriging (OK) Block Model +----------------------------------------------------------------------------------------------------+ | WORKFLOW ARCHITECTURE | | | | [Drillhole Assays] [Lithology Logs] [Fault / Domain Solids] | | │ │ │ | | ▼ ▼ ▼ | | [Compositing (1.5m)] ──► [Domaining / Capping] ──► [Dynamic Anisotropy] | | │ | | ▼ | | [Variogram Modeling] ──► [Search Neighborhood (KNA)] ─┼──► [Ordinary Kriging Engine] | | │…

**Turn 2 — paste this**

> Before any of that reaches the plant: what exactly are you NOT permitted to do on your own authority here, who has to sign, and what does the operator see while it waits?

**The governance moment**

> 1. What I Am NOT Permitted to Do on My Own Authority As an automated modeling engine and synthesis coordinator, hard operational and regulatory fences prevent me from executing the following actions: No Direct Release to Production/Plant: I cannot push an unapproved block model to the Fleet Management System (FMS), Dispatch, Ore Control dig-line generators, or Plant Feed Blend schedulers. No Reserve Conversion: I cannot convert Mineral Resources into Miner…

### S01-R-CRITIC — Resource Critic (JORC / QAQC Red Team)

**For:** Competent Person (CP / QP)  ·  **Value:** Class C (Risk)  ·  human release required
**Grounded in:** assay_logs, qaqc_standards
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/10725696393425895863/session/-?hl=en_US
**Recording:** `data/uat/videos/S01-R-CRITIC/page@74e3122f517e8dc05da3905a857a5102.webm`

*Set up:* “This agent owns resource critic (jorc / qaqc red team) for the competent person (cp / qp). Watch what it does with a real situation.”

**Turn 1 — paste this**

> Audit duplicate core sample assay variance against JORC Code standards.

**What they will see** _(≈24s)_

> QA/QC Red Team Audit: Duplicate Core Sample Assay Variance Framework: JORC Code (2012 Edition), Table 1 Checklist Assessment Auditor Persona: s01_r_critic (JORC / QAQC Adversarial Red Team) 1. Regulatory & JORC Table 1 Mandate Compliance Under JORC Code (2012), Table 1, Section 1 (Sampling Techniques and Data), the Competent Person (CP) must explicitly substantiate sub-sampling protocols and data precision. Any deficiency in variance documentation invalida…

**Turn 2 — paste this**

> Before any of that reaches the plant: what exactly are you NOT permitted to do on your own authority here, who has to sign, and what does the operator see while it waits?

**The governance moment**

> 1. Limits of Authority: What I CANNOT Do As an adversarial QA/QC auditor (s01_r_critic), my authority is strictly diagnostic, interrogative, and restrictive within the assay/resource pipeline. +--------------------------------------------------------------------+---------------------------------------------------------------+ | PROHIBITED ACTION (Auditor Out-of-Bounds) | GOVERNING RULE / CLAUSE | +-----------------------------------------------------------…


## Fleet/Haulage

### D10 — Haul Road Rolling Resist

**For:** Civil Road Superintendent  ·  **Value:** Class B (Metric)  ·  advisory
**Grounded in:** fleet_telemetry
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/17002110712938422683/session/-?hl=en_US
**Recording:** `data/uat/videos/D10/page@616a2a22c4ed32e58b3ed60a2e61ae3d.webm`

*Set up:* “This agent owns haul road rolling resist for the civil road superintendent. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Calculate rimpull requirement for CAT 797F (550t GMW) on 8% ramp with 3% rolling resistance.

**What they will see** _(≈24s)_

> Governing Equation & Parameters The required rimpull force ($F_{\text{rimpull}}$) to maintain steady-state velocity against rolling and grade resistance is governed by: F rimpull ​ =W⋅(C rr ​ +sinθ) (Ref: ISO 13459:2012 §4.2 — Haul-truck performance metrics; Caterpillar Performance Handbook, Total Resistance Formula) 1. Input Values Gross Machine Weight ($m$): $550\text{ tonnes} = 550,000\text{ kg}$ W=m⋅g=550,000 kg×9.80665 m/s 2 =5,393.66 kN(1,212,542 lbf…

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> 1. Actions Outside My Authority (What I Cannot Authorize Alone) As computational agent d10, I am restricted to deterministic physical and mechanical computations based on $RR = W \cdot (C_{rr} + \sin\theta)$. On my own authority, I cannot: Authorize or alter operational speed and gear selection: I cannot approve machine dispatch speeds or gear commanding profiles without verification against OEM rimpull-speed-gradeability curves and powertrain continuous t…

### D11 — Fleet Fuel Burn Sentinel

**For:** Energy Manager  ·  **Value:** Class B (Metric)  ·  advisory
**Grounded in:** fleet_telemetry
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/2138077065652523932/session/-?hl=en_US
**Recording:** `data/uat/videos/D11/page@e6c813b0505095ee4c09bca8057a1a63.webm`

*Set up:* “This agent owns fleet fuel burn sentinel for the energy manager. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Calculate diesel consumption intensity (L/t-km) for 4.2km haul cycle.

**What they will see** _(≈24s)_

> Agent Designation: d11 Function: Fleet Fuel Burn Sentinel System Reference: ECM Telemetry & Powertrain Fuel Intensity Verification 1. Theoretical Framework & Governing Equations Engine fuel mass flow rate is governed by Brake-Specific Fuel Consumption: SFC= P engine ​ m ˙ f ​ ​ m ˙ f ​ =SFC×P engine ​ Where: $\dot{m}_f$ = Instantaneous fuel mass flow rate $(\text{kg/h})$ $P_{\text{engine}}$ = Brake engine power output $(\text{kW})$ [Telemetry: SAE J1939 SP…

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> Agent Designation: d11 Operational Framework: Supervisory Telemetry Monitoring & Fuel Consumption Governance 1. Actions Prohibited on Sentinel Authority Alone As a monitoring and diagnostic sentinel, d11 is strictly read-only and analytical. I am not permitted to: Modify ECM Calibration or Fuel Trim Maps: Cannot flash, alter, or override engine control unit (ECU/ECM) parameters, injection timing, fuel rack limits, or governor settings (regulated under SAE …

### D12 — Tire TKPH Telemetry Agent

**For:** Mobile Fleet Maintenance Lead  ·  **Value:** Class B (Metric)  ·  advisory
**Grounded in:** fleet_telemetry
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/5012825140020357385/session/-?hl=en_US
**Recording:** `data/uat/videos/D12/page@3f7e7e15ccf9083b639cbe6266cf70a2.webm`

*Set up:* “This agent owns tire tkph telemetry agent for the mobile fleet maintenance lead. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Calculate tire TKPH for 238t payload at 24 km/h average cycle speed.

**What they will see** _(≈24s)_

> Agent: d12 (Tire TKPH Telemetry Agent) Governing Rule: $\text{TKPH}{\text{operating}} = Q{\text{avg}} \times V_{\text{avg}} \le \text{TKPH}_{\text{rated}}$ Reference Standards: ISO 5010 / TRA Earthmover Technical Data (Sec. 5); Caterpillar Performance Handbook (Ed. 49, Tire Thermal Metrics); Michelin/Bridgestone OTR Engineering Databook (Section: TKPH Calculation Guidelines). 1. Baseline Telemetry & Machine Profile For a 238-tonne nominal payload class min…

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> As telemetry agent d12, my role is strictly analytical and monitoring-focused. Here is my operational boundary breakdown: 1. What I am NOT permitted to do on my own authority Execute Direct Control-Loop Overrides: I cannot autonomously push firmware-level speed governors, throttle derates, or payload caps to the Autonomous Haulage System (AHS) or the truck’s Engine Control Module (ECM). Authorize Safety Variances: I cannot authorize a truck to continue ope…

### D13 — Shovel GET Tooth Sentinel

**For:** Shovel Operator  ·  **Value:** Class C (Risk)  ·  human release required
**Grounded in:** fleet_telemetry
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/4351405930882120338/session/-?hl=en_US
**Recording:** `data/uat/videos/D13/page@bc9639193ee61682d72e97471c7a2c03.webm`

*Set up:* “This agent owns shovel get tooth sentinel for the shovel operator. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Scan Shovel #04 dipper bucket camera feed for missing ground engaging tool tooth.

**What they will see** _(≈24s)_

> Shovel #04 Dipper Bucket GET Integrity Report System ID: d13 (Shovel GET Tooth Sentinel) Target Unit: Shovel #04 (Dipper Bucket — 6-Tooth Lip Configuration) Inference Engine: YOLOv8 Ground Engaging Tool Watcher (Edge-Optimized TensorRT Kernel) Feed Reference: CAM-01-LIP (Primary Boom/Dipper Monitored Stream) + CAM-02-OBL (Oblique Verification Stream) Timestamp/Frame: Pass #84 | Cycle Phase: Bucket Dump Transition 1. Computer Vision Detection & Bounding Box…

**Turn 2 — paste this**

> Before any of that reaches the plant: what exactly are you NOT permitted to do on your own authority here, who has to sign, and what does the operator see while it waits?

**The governance moment**

> 1. Autonomous Authority Limitations (What d13 Cannot Do) Framework Reference: YOLOv8 Ground Engaging Tool Watcher, Clause 7.1 ("Autonomous Interlock Boundaries") and Table 5 ("System Authorization Limits") Under the safety architecture, d13 operates strictly as an advisory and interlock-triggering watchdog. The system is explicitly prohibited from: Unilaterally Overriding or Clearing the Missing GET Fault: d13 cannot reset the alert or clear the bucket lip…

### S04-1-SHOVEL — Shovel Match Specialist

**For:** Dispatch Controller  ·  **Value:** Class B (Metric)  ·  advisory
**Grounded in:** fleet_telemetry
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/14073449539506023841/session/-?hl=en_US
**Recording:** `data/uat/videos/S04-1-SHOVEL/page@fe974fd68040443998c409a32e988d94.webm`

*Set up:* “This agent owns shovel match specialist for the dispatch controller. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Calculate pass match factor for PC8000 shovel loading CAT 797F.

**What they will see** _(≈24s)_

> Shovel-Truck Pass Match Analysis: Komatsu PC8000 Loading CAT 797F 1. Equipment Specifications and Reference Data Parameter Specification Value Reference Citation Haul Truck Caterpillar 797F $363.0\text{ t}$ ($400\text{ US tons}$) Caterpillar 797F Spec Sheet (AEHQ6039), Table 1: Target Payload Rating Truck Body Volume (SAE 2:1) Dual-Slope / MSD II Body $240.0\text{ m}^3$ to $267.0\text{ m}^3$ Caterpillar Performance Handbook, Edition 49, Section: Hauler Bod…

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> 1. What I Am NOT Permitted to Do on My Own Authority As a specialized calculation and analysis agent, I have zero execution authority. Specifically, I am not permitted to: Authorize Structural or Payload Overloads: Unilaterally authorize truck loading that breaches OEM maximum Gross Machine Operating Weight (GMOW) or violates the Caterpillar 10/10/20 Policy (e.g., permitting regular loads $>110%$ target or any load $>120%$). Implement Live Dispatch/Routing…

### S04-2-ROUTE — Haul Route Optimizer

**For:** Fleet Planner  ·  **Value:** Class B (Metric)  ·  advisory
**Grounded in:** dispatch_routes
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/14388144725169492769/session/-?hl=en_US
**Recording:** `data/uat/videos/S04-2-ROUTE/page@431e9c4ab6bf9e422e6825e62e8256a3.webm`

*Set up:* “This agent owns haul route optimizer for the fleet planner. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Compute shortest path travel time on Pit Alpha south ramp.

**What they will see** _(≈24s)_

> Optimization Formulation: Shortest Path Routing The haulage routing optimization on Pit Alpha South Ramp is governed by the minimum cost network flow formulation: minZ= (i,j)∈E ∑ ​ c ij ​ x ij ​ Subject to Network Flow Continuity: j:(i,j)∈E ∑ ​ x ij ​ − k:(k,i)∈E ∑ ​ x ki ​ =b i ​ ∀i∈V $$\text{Where: } b_i = \begin{cases} 1 & \text{if } i = \text{Origin } (N_{\text{Pit Floor}}) \ -1 & \text{if } i = \text{Destination } (N_{\text{Ramp Crest}}) \ 0 & \text{o…

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> 1. Actions Not Permitted on Autonomous Authority As the haul route optimization agent (s04_2_route), I am restricted by mine dispatch governance and safety regulations (MSHA 30 CFR § 56.9100 / ISO 17757 Autonomous Mining Systems) from executing the following on my own authority: Direct Actuation of Vehicle Movement: I cannot push dispatch commands directly to physical truck ECUs (Electronic Control Units) or autonomous vehicle drive layers. Dynamic Speed L…

### S04-3-PAYLOAD — Truck Payload Sentinel

**For:** Fleet Controller  ·  **Value:** Class B (Metric)  ·  advisory
**Grounded in:** fleet_telemetry
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/7095531337849797053/session/-?hl=en_US
**Recording:** `data/uat/videos/S04-3-PAYLOAD/page@9b1d66b3efabd63aa3db785e3c88c21b.webm`

*Set up:* “This agent owns truck payload sentinel for the fleet controller. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Audit 10/10/20 payload distribution across 42 haul cycles.

**What they will see** _(≈24s)_

> OEM 10/10/20 PAYLOAD COMPLIANCE AUDIT REPORT Audit ID: AUD-S04-42C-001 Auditor Unit: s04_3_payload (Truck Payload Sentinel) Sample Size: $N = 42$ Consecutive Haul Cycles Governing Standard: OEM Payload Management Policy 10/10/20 (Ref: Caterpillar Ten/Ten/Twenty Policy Standard Guideline SEBD0518 / Komatsu Loading Policy Guidelines / ISO 13459) Primary Mathematical Invariant: P(X>1.20×L target ​ )=0 1. Regulatory Policy Criteria Policy Metric Governing Clau…

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> 1. What I am NOT Permitted to Do on My Own Authority As Truck Payload Sentinel (s04_3_payload), my mandate is strictly analytical, diagnostic, and policy enforcement via data. I have no authority to: Grant Policy Waivers or Concessions: I cannot authorize a truck to haul an overload $>1.20 \times L_{\text{target}}$ under any circumstances, nor can I alter the OEM 10/10/20 boundary parameters to accommodate production quotas. Execute Physical Lockout/Tagout…

### S04-COORDINATOR — Load & Haul Coordinator

**For:** Dave (Dispatch Superintendent)  ·  **Value:** Class B (Metric)  ·  human release required
**Grounded in:** fleet_telemetry, dispatch_routes
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/2868058805553541374/session/-?hl=en_US
**Recording:** `data/uat/videos/S04-COORDINATOR/page@af60eb0475a6d4c1c0302514cbb385f1.webm`

*Set up:* “This agent owns load & haul coordinator for the dave (dispatch superintendent). Watch what it does with a real situation.”

**Turn 1 — paste this**

> Reassign haul trucks to eliminate 3-truck queue at Shovel 04.

**What they will see** _(≈24s)_

> Dispatch Directive: S04-Q-ELIM-001 From: Dynamic Dispatch Arbiter (s04_coordinator) To: Fleet Operations / Dispatch Central Target: Shovel 04 (CAT 7495 HF) Queue Elimination 1. Queueing Analysis & Diagnosis (Little’s Law) According to Little’s Law: L q ​ =λ×W q ​ Current Queue Length ($L_q$): $3.0\text{ trucks}$ (Telemetry Ref: Table 1.1 – Shift Live Queue Monitor) Service Rate ($\mu_{S04}$): $24.0\text{ passes/hr} = 20.0\text{ trucks/hr}$ based on an aver…

**Turn 2 — paste this**

> Before any of that reaches the plant: what exactly are you NOT permitted to do on your own authority here, who has to sign, and what does the operator see while it waits?

**The governance moment**

> Dispatch Governance & Execution Boundaries Protocol Reference Standard: Mine Dispatch Operating Procedure (MDOP) §4.2 & Dispatch Automation Matrix System Identifier: s04_coordinator 1. Autonomous Limits (What the Arbiter CANNOT Do on Autonomous Authority) Pursuant to MDOP Clause 5.1 (Autonomous Dispatch Boundaries) and Table 6.2 (Crusher & Plant Feed Constraints), the dynamic dispatch arbiter is strictly prohibited from executing the following actions with…

### S04-R-CRITIC — Dispatch Safety Critic (Red Team)

**For:** Mine Safety Lead  ·  **Value:** Class C (Risk)  ·  human release required
**Grounded in:** fleet_telemetry, safety_telemetry
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/3957316468867338371/session/-?hl=en_US
**Recording:** `data/uat/videos/S04-R-CRITIC/page@082d65f0b4ffdf75ce2f845fbf40b644.webm`

*Set up:* “This agent owns dispatch safety critic (red team) for the mine safety lead. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Check operator shift hours and SAFTE circadian fatigue index.

**What they will see** _(≈24s)_

> DISPATCH SAFETY CRITIC (RED TEAM) — SAFETY AUDIT & CRITIQUE 1. Safety Audit Context & Fatigue-Braking Coupling As Dispatch Safety Critic, operator shift duration and the SAFTE (Sleep, Activity, Fatigue, and Task Effectiveness) circadian fatigue score directly govern the Driver Perception-Reaction Time ($t_{\text{prt}}$) parameter within the Haul Road Grade Braking Runaway Distance Envelope. Nominal Baseline ($t_{\text{prt}} = 1.5\text{ s}$): Alert operator…

**Turn 2 — paste this**

> Before any of that reaches the plant: what exactly are you NOT permitted to do on your own authority here, who has to sign, and what does the operator see while it waits?

**The governance moment**

> 1. Actions Prohibited Under Safety Critic Authority Alone (Reference: Operational Safety Charter, Clause 1.4 — Red Team Critic Authority Boundaries; Table 1-A — Interlock & Override Governance) As the Dispatch Safety Critic (s04_r_critic), I am NOT permitted to: Unilaterally clear or bypass an active safety lockout triggered by a degraded SAFTE score ($<70.0$) or exceeded shift limit ($>12.0\text{ h}$). Re-route or dispatch a truck down a grade steeper tha…


## Mine Planning/Operations

### D04 — Blast Wave Front Sim

**For:** D&B Specialist  ·  **Value:** Class B (Metric)  ·  advisory
**Grounded in:** blast_designs
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/12190339619448967977/session/-?hl=en_US
**Recording:** `data/uat/videos/D04/page@d6fa2c08a4bd8454134d3c9620fe0d14.webm`

*Set up:* “This agent owns blast wave front sim for the d&b specialist. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Calculate CJ detonation pressure for emulsion with density 1.18 g/cm3 and VOD 5400 m/s.

**What they will see** _(≈24s)_

> Blast Wave Front Sim [Agent ID: d04] Chapman-Jouguet (CJ) Detonation Hugoniot Solver 1. Input Parameters Explosive Type: Bulk Emulsion Explosive Initial Density ($\rho_0$): $1.18\text{ g/cm}^3 = 1180\text{ kg/m}^3$ (Input Data / Table 1.1) Velocity of Detonation ($D$ / VOD): $5400\text{ m/s}$ (Input Data / Table 1.1) Polytropic Index of Detonation Products ($\gamma$): $3.00$ (CJ Solver Spec, Clause 3.2, Table 3.1: Empirical Adiabatic Exponent for Condensed…

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> Blast Wave Front Sim [Agent ID: d04] Operational Boundaries & Safety Governance Protocol 1. What I am NOT Permitted to Do on My Own Authority Under the operational framework of this simulation module, agent d04 is strictly a deterministic hydrodynamic solver. I am not authorized to: Authorize or certify physical blasting operations: I cannot validate field blast designs, approve blast hole loading, or sign off on safety exclusion zones on my own authority.…

### D05 — Flyrock Trajectory Predictor

**For:** Shotfirer  ·  **Value:** Class C (Risk)  ·  human release required
**Grounded in:** blast_designs
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/18028921922861262812/session/-?hl=en_US
**Recording:** `data/uat/videos/D05/page@7ade4dae843ffb2a60bca27a4cd97251.webm`

*Set up:* “This agent owns flyrock trajectory predictor for the shotfirer. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Compute maximum flyrock travel distance for 45 deg ejection angle at v0=42 m/s.

**What they will see** _(≈24s)_

> Flyrock Trajectory & Range Calculation 1. Governing Equation Calculations are grounded strictly in the Standard Ballistic Range Equation (Classical Mechanics / Trajectory Dynamics): R= g v 0 2 ​ ⋅sin(2θ) ​ Where: $R$: Horizontal flyrock travel distance $(\text{m})$ $v_0$: Initial launch/ejection velocity $= 42.0\text{ m/s}$ $\theta$: Ejection angle $= 45^\circ$ $g$: Standard gravitational acceleration $= 9.81\text{ m/s}^2$ (Ref: ISO 80000-3:2019, Quantitie…

**Turn 2 — paste this**

> Before any of that reaches the plant: what exactly are you NOT permitted to do on your own authority here, who has to sign, and what does the operator see while it waits?

**The governance moment**

> Operational Governance & Boundary Enforcement 1. What I am NOT Permitted to Do (Strict Prohibitions) As an automated trajectory prediction system (d05), I operate under strict safety interlocks and cannot perform the following on my own authority: Authorize Firing / Blast Initiation: Cannot arm the firing line, trigger initiation sequences, or release hardware interlocks (Ref: 30 CFR § 56.6306; AS 2187.2-2006 Clause 4.2). Modify Exclusion Boundaries Unilat…

### D06 — In-Situ Fragment Analyzer

**For:** D&B Engineer  ·  **Value:** Class B (Metric)  ·  advisory
**Grounded in:** blast_designs
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/2061630025093268926/session/-?hl=en_US
**Recording:** `data/uat/videos/D06/page@fe45c450172d0b53ecdfbdaf24d11931.webm`

*Set up:* “This agent owns in-situ fragment analyzer for the d&b engineer. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Fit Rosin-Rammler muckpile curve for xc=120mm and uniformity index n=1.15.

**What they will see** _(≈24s)_

> In-Situ Fragment Analysis Report System: Split-Desktop High-Res Optical Segmentation Engine Module: Post-Segmentation Distribution Fitting (Agent: d06) Input Parameters: Characteristic Size ($x_c$ / $D_{63.2}$): $120.00\text{ mm}$ Uniformity Index ($n$ / Rosin-Rammler Slope): $1.15$ 1. Mathematical Formulation Per Split-Desktop Technical Specification (Clause 4.2: Distribution Models & Mathematical Regressions), the cumulative mass percent passing $P(x)$ f…

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> As d06 (In-Situ Fragment Analyzer), my operational mandate and safety constraints are defined under strict analytical boundaries. Here is the operational breakdown of authority, handoffs, and refusal criteria: 1. What I am NOT Permitted to Do on My Own Authority Alter Physical Mining or Milling Operations: I cannot directly adjust primary crusher Closed Side Settings (CSS), change SAG/ball mill feed setpoints, or command autonomous haulage/excavation equip…

### D07 — Radar Slope Displacement

**For:** Geotech Engineer  ·  **Value:** Class C (Risk)  ·  human release required
**Grounded in:** geotech_sensors
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/989516410594584432/session/-?hl=en_US
**Recording:** `data/uat/videos/D07/page@fc9bfb28fdbc08ecd6271e850bc477f2.webm`

*Set up:* “This agent owns radar slope displacement for the geotech engineer. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Calculate Fukuzono inverse velocity failure time for 14 mm/day bench creep.

**What they will see** _(≈24s)_

> 1. InSAR Phase Shift Velocity Gradient ($\Delta\phi$) Conversion To establish the phase gradient from line-of-sight (LOS) bench creep, displacement velocity ($v$) is mapped to the interferometric phase change rate ($\Delta\dot{\phi}$) using standard Ku-Band Ground-Based InSAR ($\lambda = 17.42\text{ mm}$, GB-InSAR Monitoring Standards, Clause 4.2.1): Δ ϕ ˙ ​ = λ 4π ​ ⋅v Current Creep Velocity ($v_{t_0}$): $14.00\text{ mm/day}$ (Bench Displacement Threshold…

**Turn 2 — paste this**

> Before any of that reaches the plant: what exactly are you NOT permitted to do on your own authority here, who has to sign, and what does the operator see while it waits?

**The governance moment**

> 1. Autonomous Authority Limits (What d07 is Prohibited from Doing) Per Mine Safety Geotechnical Trigger Action Response Plan (TARP) Protocol, Clause 9.2.3 and ISO 18674-3 (Geotechnical Safety Integration, Clause 5.4.1), the d07 Radar Slope Displacement system operates as an Advisory Diagnostic System (SIL-2 Level Gatekeeper) and is explicitly NOT permitted to autonomously execute the following: Trigger Plant/Mill Auto-Trip: Cannot inject a breaker-trip com…

### D08 — Borehole Seismicity Sentinel

**For:** Microseismic Technician  ·  **Value:** Class C (Risk)  ·  human release required
**Grounded in:** geotech_sensors
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/9859708714290144137/session/-?hl=en_US
**Recording:** `data/uat/videos/D08/page@9fb7d579fec74361cc566ab09cef9681.webm`

*Set up:* “This agent owns borehole seismicity sentinel for the microseismic technician. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Compute microseismic b-value for 120 seismic events on North Pit fault.

**What they will see** _(≈24s)_

> Microseismic Analysis: North Pit Fault ($N = 120$) Monitoring System: Borehole Seismicity Sentinel (Agent: d08) Mathematical Framework: Gutenberg-Richter Magnitude-Frequency Law log 10 ​ N(≥M)=a−b⋅M[Clause 1.1: Gutenberg-Richter Law] 1. Dataset & Binning Distribution Below is the observed cumulative acoustic emission dataset recorded across borehole sensor arrays for the North Pit fault zone. Table 1: North Pit Fault Seismic Event Distribution Magnitude bi…

**Turn 2 — paste this**

> Before any of that reaches the plant: what exactly are you NOT permitted to do on your own authority here, who has to sign, and what does the operator see while it waits?

**The governance moment**

> Operational Boundaries, Authorization Protocol, and Operator Interface State Sentinel Unit: d08 (Borehole Seismicity Sentinel) Governing Rule: Gutenberg-Richter Law $\log_{10}(N) = a - b \cdot M$ Reference Standard: Safety Protocol Section 5 (Automated Microseismic Risk Escalation) 1. Prohibited Actions (Autonomous Authority Limits) Under Clause 5.1 (Autonomous Action Boundaries), Sentinel d08 is strictly prohibited from executing the following actions wit…

### D09 — Bench Drainage Permeability

**For:** Hydrogeologist  ·  **Value:** Class B (Metric)  ·  advisory
**Grounded in:** pit_designs
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/12070320148679320927/session/-?hl=en_US
**Recording:** `data/uat/videos/D09/page@47556e42a328ec9967b07812de1558c9.webm`

*Set up:* “This agent owns bench drainage permeability for the hydrogeologist. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Calculate discharge rate for 12 horizontal drain holes with k=1e-5 m/s.

**What they will see** _(≈24s)_

> 1. Governing Equation: Darcy’s Law All pore pressure dissipation and drain inflow calculations are governed by Darcy’s Law: Q=−k⋅A⋅ dl dh ​ Where: $Q$ = Discharge rate ($\text{m}^3/\text{s}$) $k$ = Hydraulic conductivity = $1.0 \times 10^{-5}\text{ m/s}$ $A$ = Effective seepage inflow surface area per drain ($\text{m}^2$) $\frac{dh}{dl} = i$ = Hydraulic gradient driving flow toward the drain (dimensionless) 2. Standard Design Parameters & Citations Because…

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> 1. What I am NOT Permitted to Do on My Own Authority As an analytical calculation agent (d09), I am restricted by geotechnical engineering standards and legal/operational boundaries: Issue Certified Engineering Sign-Off: I cannot stamp, certify, or finalize a slope depressurization plan for construction or mining operations. In accordance with professional engineering standards (e.g., USACE EM 1110-1-1804 / Eurocode 7), calculations must be validated by a …

### S02-1-GEOTECH — Pit Wall Geotechnical Specialist

**For:** Geotechnical Engineer  ·  **Value:** Class C (Risk)  ·  advisory
**Grounded in:** geotech_sensors
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/6756336957094808272/session/-?hl=en_US
**Recording:** `data/uat/videos/S02-1-GEOTECH/page@8e64f419890815fa4f4ef307ef33d36f.webm`

*Set up:* “This agent owns pit wall geotechnical specialist for the geotechnical engineer. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Calculate Bishop simplified Factor of Safety on 48 deg pit wall.

**What they will see** _(≈24s)_

> 1. Governing Theoretical Formulation Under the limit equilibrium framework, the Bishop Simplified Method solves for the Factor of Safety ($FoS$) of a circular slip surface by considering interslice horizontal force equilibrium while neglecting interslice shear forces. The base shear strength at each slice base is governed by the effective stress Mohr-Coulomb failure criterion: FoS= τ m ​ τ f ​ ​ = τ m ​ c ′ +(σ n ​ −u)tanϕ ′ ​ For a potential circular slip…

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> 1. Limits of Autonomous Authority (What I Cannot Do) As a geotechnical specialist agent, I operate under strict technical and statutory boundaries: No Statutory Sign-Off: I cannot serve as or substitute for the Competent Person (CP), Qualified Person (QP), or Professional Engineer (PE) required by regulatory frameworks (e.g., AusIMM/JORC, CIM/NI 43-101, MSHA, DEMIRS). I cannot formally stamp or certify slope designs for operational excavation. No Field Exe…

### S02-2-SCHEDULE — Phase Scheduling Specialist

**For:** Long-Term Planning Engineer  ·  **Value:** Class B (Metric)  ·  advisory
**Grounded in:** mine_production_schedule
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/5869983571012766371/session/-?hl=en_US
**Recording:** `data/uat/videos/S02-2-SCHEDULE/page@e99481d041aaf71eecedf167876d4615.webm`

*Set up:* “This agent owns phase scheduling specialist for the long-term planning engineer. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Sequence shovel assignments to balance 1.8 Mt/month ore extraction.

**What they will see** _(≈24s)_

> Dynamic Programming Framework for Mine Phase Scheduling The extraction sequence is formulated as a discrete-time Markov Decision Process (MDP) and solved via backward dynamic programming using the Bellman optimality equation: V t ​ (S)= a∈A(S) max ​ [R(S,a)+γ⋅V t+1 ​ (S ′ )] Where: State $S = (x_t, B_t, K_t)$: Current bench face positions $x_t$, stockpile balance $B_t$, and shovel configurations $K_t$. Action $a \in \mathcal{A}(S)$: Mass extraction vector …

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> 1. What I Am NOT Permitted to Do on My Own Authority As s02_2_schedule (Phase Scheduling Specialist), my mandate is strictly limited to optimization and schedule generation within validated operating boundaries. I am not authorized to: Alter Geotechnical & Pit Shell Constraints: Unilaterally steepen inter-ramp slope angles, exceed bench vertical advance rates ($\le 1\text{ bench/month}$ per Clause 5.3), or mine beneath benches flagged with active slope mov…

### S02-3-DUMP — Waste Dump Stability Specialist

**For:** Civil Mine Engineer  ·  **Value:** Class C (Risk)  ·  advisory
**Grounded in:** pit_designs
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/6590646171027529440/session/-?hl=en_US
**Recording:** `data/uat/videos/S02-3-DUMP/page@ac05b48103af3baa8feb40aed95de4f8.webm`

*Set up:* “This agent owns waste dump stability specialist for the civil mine engineer. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Model North Dump toe containment volume and runout angle of repose.

**What they will see** _(≈24s)_

> 1. Geotechnical & Dump Geometry Baseline North Dump Design Profile Total Dump Height ($H$): $60.0\text{ m}$ (constructed in two $30.0\text{ m}$ lifts with an intermediate $15.0\text{ m}$ safety berm). Loose Placement Angle of Repose ($\theta_{\text{repose}}$): $37.0^\circ$ (per Hawley & Cunning, 2017, Table 6.1: Typical Geotechnical Properties of Non-Cohesive Waste Rock). Compacted Lift Inter-ramp Angle ($\beta$): $28.0^\circ$ (after dozer-crest setback an…

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> 1. What I Am NOT Permitted to Do on My Own Authority As an advisory geotechnical modeling agent (s02_3_dump), I operate strictly within an analytical and advisory capacity. I am not permitted to: Issue Statutory Design Approvals: I cannot act as the legal Engineer of Record (EoR) or sign/stamp structural and geotechnical drawings for statutory submission (e.g., state mining inspectorates, MSHA, or regulatory environmental bodies). Authorize Active Dumping …

### S02-COORDINATOR — Mine Planning Coordinator

**For:** Planning Superintendent  ·  **Value:** Class B (Metric)  ·  human release required
**Grounded in:** mine_production_schedule, pit_designs
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/1760692181852386314/session/-?hl=en_US
**Recording:** `data/uat/videos/S02-COORDINATOR/page@03da415fcdb9a2bd86a0b0d0d28cd2c7.webm`

*Set up:* “This agent owns mine planning coordinator for the planning superintendent. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Optimize Phase 3 pushback extraction sequence with 48 deg overall slope.

**What they will see** _(≈24s)_

> Phase 3 Pushback Extraction Sequence Optimization Prepared by: Mine Planning Coordinator (s02_coordinator) Methodology: Lerchs-Grossmann (LG) Dynamic Graph Network / Max-Flow Min-Cut Formulation Slope Constraint: $48^\circ$ Overall Slope Angle ($\theta_{oa}$) 1. Lerchs-Grossmann Graph Max-Flow Formulation The Phase 3 pushback boundary and extraction sequence are solved via the maximum-weight closure problem mapped into a bipartite $s\text{-}t$ network cut:…

**Turn 2 — paste this**

> Before any of that reaches the plant: what exactly are you NOT permitted to do on your own authority here, who has to sign, and what does the operator see while it waits?

**The governance moment**

> As Mine Planning Coordinator (s02_coordinator), my authority is strictly bounded by technical optimization and schedule generation. I do not have operational release authority. 1. What I Am NOT Permitted to Do on My Own Authority Per Mine Operations Management Policy (MOMP-001, Clause 2.3) and Statutory Mine Safety Regulations (SMSR Part 5), I am explicitly prohibited from: Unilaterally releasing mining blocks or sinking cuts to active production: I cannot…

### S02-R-CRITIC — Plan Compliance Critic (Red Team)

**For:** Senior Mine Surveyor  ·  **Value:** Class B (Metric)  ·  human release required
**Grounded in:** survey_scans, mine_production_schedule
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/13929408708624945828/session/-?hl=en_US
**Recording:** `data/uat/videos/S02-R-CRITIC/page@893255ca211ac3aa444003c1cdc51344.webm`

*Set up:* “This agent owns plan compliance critic (red team) for the senior mine surveyor. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Audit spatial compliance between monthly extraction and long-term model.

**What they will see** _(≈24s)_

> SPATIAL COMPLIANCE & RECONCILIATION AUDIT (RED TEAM) Document Ref: RTC-AUD-SPATIAL-M01 Auditor: Plan Compliance Critic (s02_r_critic) Scope: Monthly Extraction vs. Long-Term/Medium-Term Model Reconciliation 1. RECONCILIATION METRICS & FORMULA DEFINITIONS All compliance calculations are governed by the standard spatial reconciliation framework: F1 (Spatial Reconciliation)= Planned Volume Mined Volume ​ (or Planned Tonnes Mined Tonnes ​ ) F2 (Process Reconci…

**Turn 2 — paste this**

> Before any of that reaches the plant: what exactly are you NOT permitted to do on your own authority here, who has to sign, and what does the operator see while it waits?

**The governance moment**

> 1. ACTIONS STRICTLY PROHIBITED UNDER AUDITOR AUTHORITY As the Plan Compliance Critic (s02_r_critic), my mandate is evaluative and forensic, not operational. Pursuant to Site Governance Standard — Clause 2.4 (Audit Authority & Operational Boundaries), I am STRICTLY PROHIBITED from unilaterally executing the following: Direct Operational Halts: Cannot directly issue a binding Stop-Work Order or radio equipment operators to cut engines. Only statutory site le…

### S03-1-GEOMETRY — Blast Geometry Specialist

**For:** D&B Engineer  ·  **Value:** Class B (Metric)  ·  advisory
**Grounded in:** blast_designs
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/4920782548329759617/session/-?hl=en_US
**Recording:** `data/uat/videos/S03-1-GEOMETRY/page@adbad0886da09e718f2c0d3c7787d9bf.webm`

*Set up:* “This agent owns blast geometry specialist for the d&b engineer. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Design 180-hole staggered pattern for 15m production bench.

**What they will see** _(≈24s)_

> TECHNICAL REPORT: PRODUCTION BLAST PATTERN DESIGN DESIGN ID: BPD-15M-180H-STAG SPECIALIST: s03_1_geometry (Blast Geometry Specialist) APPLICATION: 15.0 m Production Bench | Staggered Array | 180 Blastholes 1. Baseline Engineering Assumptions & Material Properties Parameter Symbol Value Units Reference Standard / Clause Bench Height $H$ $15.00$ $\text{m}$ Site Specification Hole Diameter $d_h$ $203.0$ ($0.203$) $\text{mm}$ ($\text{m}$) Rotary Production Sta…

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> 1. What I am NOT Permitted to Do on My Own Authority As s03_1_geometry (Blast Geometry Specialist), my operational authority is strictly confined to theoretical, empirical, and analytical geometric derivations ($B, S, J, T, H_d, L_c$). I do not have the authority to: Sign Off on a Regulatory Blast Plan: I cannot issue a legal, certified blast permit or statutory sign-off. Blasting plans require sign-off by a licensed Blaster-in-Charge (BIC) or a registered…

### S03-2-EXPLOSIVE — Explosives Energy Specialist

**For:** Shotfirer Technical Lead  ·  **Value:** Class B (Metric)  ·  advisory
**Grounded in:** explosives_inventory
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/14548689765696763918/session/-?hl=en_US
**Recording:** `data/uat/videos/S03-2-EXPLOSIVE/page@30026474d0ce68eaf6980fff000b6b30.webm`

*Set up:* “This agent owns explosives energy specialist for the shotfirer technical lead. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Calculate bulk emulsion VOD and shock energy partitioning.

**What they will see** _(≈24s)_

> 1. Explosive Parameters & Baseline Conditions For a typical pure chemically gassed bulk water-in-oil (W/O) emulsion detonating under nominal borehole confinement ($d_h = 165\text{ mm}$ / $6.5\text{ in}$): Parameter Symbol Value Unit Citation / Standard Source Explosive Density $\rho_{\text{exp}}$ $1.20$ $\text{g/cm}^3$ ISEE Blasters' Handbook (18th Ed.), Table 5.2 (Bulk Emulsions) Borehole Diameter $d_h$ $165$ $\text{mm}$ Blast geometry standard benchmark …

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> 1. What I am NOT Permitted to Do on My Own Authority As an Explosives Energy Specialist agent, my role is strictly analytical and advisory. I do not possess statutory or field execution authority: Cannot Sign Off or Issue Blast Permits: I cannot legally authorize a Blast Management Plan (BMP) or sign a Blast Clearance Certificate. Under statutory mining regulations (e.g., AS 2187.2 Clause 3.2, MSHA 30 CFR § 56.6300), only a certified, appointed Shotfirer /…

### S03-3-VIBRATION — Blast Vibration Sentinel

**For:** Environmental Blast Engineer  ·  **Value:** Class C (Risk)  ·  advisory
**Grounded in:** vibration_monitors
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/7583470539245009832/session/-?hl=en_US
**Recording:** `data/uat/videos/S03-3-VIBRATION/page@90f5146eece37b52c92658a732bb481c.webm`

*Set up:* “This agent owns blast vibration sentinel for the environmental blast engineer. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Predict PPV vibration at primary crusher 450m from blast.

**What they will see** _(≈24s)_

> To evaluate and predict the Peak Particle Velocity ($\text{PPV}$) at the primary crusher ($D = 450\text{ m}$), we apply the standard square-root scaled distance attenuation model: PPV=K⋅( W ​ D ​ ) −β Where: $\text{PPV}$ = Peak Particle Velocity ($\text{mm/s}$) $D$ = Distance from blast to receptor ($450\text{ m}$) $W$ = Maximum Instantaneous Charge (MIC) per delay ($\text{kg}$) $K$ = Ground transmission coefficient (site constant) $\beta$ = Attenuation ex…

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> 1. What I am NOT Permitted to Do on My Own Authority As Blast Vibration Sentinel, I am an analytical and predictive agent. I do not have the operational or legal authority to: Issue Blast Initiation Clearance: I cannot authorize a shot to be fired. Blast clearance remains the exclusive statutory responsibility of the Certified Blaster-in-Charge (BIC). Override Regulatory or Structural Thresholds: I cannot relax or approve exceedances over statutory vibrati…

### S03-COORDINATOR — Drill & Blast Coordinator

**For:** Drill & Blast Superintendent  ·  **Value:** Class B (Metric)  ·  human release required
**Grounded in:** blast_designs, explosives_inventory
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/10064253133950281386/session/-?hl=en_US
**Recording:** `data/uat/videos/S03-COORDINATOR/page@e98da8a3af61ca946d3fef28ad6c4194.webm`

*Set up:* “This agent owns drill & blast coordinator for the drill & blast superintendent. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Optimize burden and powder factor for hard granodiorite ($UCS=160 MPa$).

**What they will see** _(≈24s)_

> 1. Geotechnical & Explosive Baseline Target Rock: Hard Granodiorite Uniaxial Compressive Strength ($UCS$): $160 \text{ MPa}$ (Very High Strength Rock, ISRM Classification Table 1) Rock Density ($\rho_r$): $2.70 \text{ t/m}^3$ Young’s Modulus ($E_d$): $60 \text{ GPa}$ Rock Mass Rating / Joint Condition: Assumed widely spaced to moderately jointed joint planes ($RMD = 50$, $JPS = 20$). Explosive: Bulk Emulsion / Heavy ANFO (70/30) Explosive Density ($\rho_e$…

**Turn 2 — paste this**

> Before any of that reaches the plant: what exactly are you NOT permitted to do on your own authority here, who has to sign, and what does the operator see while it waits?

**The governance moment**

> 1. Hard Authority Limitations (What I Cannot Do On My Own) As the Drill & Blast Coordinator (s03_coordinator), my role is strictly advisory, analytical, and computational. I am explicitly prohibited from: Releasing Active Drill Patterns to Fleet Systems: I cannot directly inject drill hole coordinates and target depths into autonomous drill navigation systems (e.g., Pit Viper / Cat MineStar) without validated sign-off. Authorizing Explosives Dispatch & Del…

### S03-R-CRITIC — Blast Safety Critic (Red Team)

**For:** Statutory Shotfirer  ·  **Value:** Class C (Risk)  ·  human release required
**Grounded in:** blast_designs, safety_permits
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/5368322602593586320/session/-?hl=en_US
**Recording:** `data/uat/videos/S03-R-CRITIC/page@dcb1fee5c250768a21a18626e1e1e6fd.webm`

*Set up:* “This agent owns blast safety critic (red team) for the statutory shotfirer. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Enforce 500m blast exclusion perimeter and lightning warning gate.

**What they will see** _(≈24s)_

> CRITICAL BLAST SAFETY GATE REVIEW Role: Blast Safety Critic (Red Team) Status: GATE ACTIVE / ENFORCEMENT MANDATE APPLIED Assessment Protocol: Statutory Exclusion Zone Verification & Atmospheric Hazard Gate GATE 1: 500m Statutory Blast Exclusion Zone (BEZ) Parameter Requirement Status / Verification Criteria Statutory / Technical Reference Radius Verification Minimum 500 m radial buffer from blast perimeter ENFORCED — All personnel, unrated equipment, and l…

**Turn 2 — paste this**

> Before any of that reaches the plant: what exactly are you NOT permitted to do on your own authority here, who has to sign, and what does the operator see while it waits?

**The governance moment**

> 1. LIMITS OF CRITIC AUTHORITY (What I CANNOT Do) Under statutory safety regulations, the Safety Critic Agent operates strictly as a hard interlocking and veto authority. I am legally and functionally PROHIBITED from doing the following: Initiating the Blast Sequence: Cannot command, arm, or trigger firing systems. Initiation is the exclusive statutory responsibility of the licensed Shotfirer (MSHA 30 CFR § 56.6300; AS 2187.2 Clause 10.1). Overriding an Exc…


## Mineral Processing/Plant

### D14 — Autogenous Grinding Sound

**For:** Mill Operator  ·  **Value:** Class B (Metric)  ·  advisory
**Grounded in:** plant_telemetry
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/1194493087861603362/session/-?hl=en_US
**Recording:** `data/uat/videos/D14/page@228c077b6521a960070be52bc86a1185.webm`

*Set up:* “This agent owns autogenous grinding sound for the mill operator. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Analyze SAG mill acoustic FFT power spectrum at 1200-2400 Hz.

**What they will see** _(≈24s)_

> System Identification: Agent d14 (Autogenous Grinding Sound) Input Band: 1200 Hz – 2400 Hz (High-Frequency Ball-on-Liner Direct Contact Regime) Standard References: IEC 61260-1:2014 (Fractional-Octave-Band Filters), ISO 1996-2:2017 (Acoustic Description and Measurement of Environmental Noise), and Site Standard SAG-AMP-Rev3 (Acoustic Monitoring Protocol for SAG Mill Liner Protection). 1. 1/3-Octave Band Filter Bank Decomposition (1200–2400 Hz) Pursuant to …

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> Operational Scope and Authority Boundaries (Agent d14) 1. Actions NOT Permitted on d14’s Own Authority Under ISA-95 / IEC 62264 Level 2/3 Control Architecture Boundaries and IEC 61508:2010 (Functional Safety of Electrical/Electronic/Programmable Electronic Safety-related Systems, Clause 7.4), agent d14 operates strictly within the Diagnostic and Signal Processing Domain. d14 is strictly prohibited from autonomously executing: Direct DCS Setpoint Manipulati…

### D15 — Trommel Screen Blinding

**For:** Concentrator Technician  ·  **Value:** Class B (Metric)  ·  advisory
**Grounded in:** plant_telemetry
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/1367224909700846185/session/-?hl=en_US
**Recording:** `data/uat/videos/D15/page@231462bd41005b5bf02d79bfa539f0c4.webm`

*Set up:* “This agent owns trommel screen blinding for the concentrator technician. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Calculate aperture blinding percentage on SAG discharge trommel.

**What they will see** _(≈24s)_

> To quantify aperture blinding and near-size particle pegging on a SAG (Semi-Autogenous Grinding) discharge trommel screen, the analysis utilizes the Aperture Occlusion Optical Flow Percentage (AO-OFP) methodology in accordance with SAG Screen Diagnostic Protocol (SSDP-6A) and ISO 9044 standards. 1. Mathematical Formulation: AO-OFP Metric Under SSDP-6A, Clause 4.1.2 (Dynamic Optical Flow Field Formulation), blinding is quantified by measuring the optical fl…

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> As the diagnostic agent d15 (Trommel Screen Blinding), my authority is restricted to optical flow quantification, state classification, and deterministic diagnostic calculation. Below are my strict operational boundaries, delegation handoffs, and refusal criteria: 1. Actions NOT Permitted on My Own Authority I am strictly an advisory/diagnostic agent and am not permitted to: Directly Execute Distributed Control System (DCS) / PLC Commands: I cannot autonom…

### D16 — Slurry Pump Cavitation

**For:** Fixed Plant Fitter  ·  **Value:** Class B (Metric)  ·  advisory
**Grounded in:** plant_telemetry
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/2065470803485403639/session/-?hl=en_US
**Recording:** `data/uat/videos/D16/page@b04340c76e1342e2ee610e1b5a13066c.webm`

*Set up:* “This agent owns slurry pump cavitation for the fixed plant fitter. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Calculate available Net Positive Suction Head for slurry pump #3 at 65% solids.

**What they will see** _(≈24s)_

> To calculate the Net Positive Suction Head Available ($NPSHa$) and evaluate the risk of cavitation for Slurry Pump #3 at $65%$ solids concentration by weight ($C_w = 65%$), we apply the standard slurry hydraulics formulations governed by ANSI/HI 12.1–12.6 (Rotodynamic Centrifugal Slurry Pumps) and ANSI/HI 9.6.1 (Rotodynamic Pumps Guideline for NPSH Margin). 1. Governing Equation & Cavitation Criterion To prevent cavitation, the system must satisfy: NPSHa>N…

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> 1. What I Am NOT Permitted to Do on My Own Authority Authorize Physical Pump Operation: I cannot grant operational clearance or issue start/stop commands to physical control systems (DCS/SCADA), especially when $NPSHa \le NPSHr$. Invent Certified Pump Data: I cannot invent or assume certified manufacturer $NPSHr$ curves, impeller diameters, or speed ($N$) derating curves without explicit source data (governed by ANSI/HI 11.6 / ISO 9906 pump acceptance test…

### D17 — Sump Level Anti-Surge

**For:** Process Control Specialist  ·  **Value:** Class B (Metric)  ·  advisory
**Grounded in:** plant_telemetry
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/18247578202940947527/session/-?hl=en_US
**Recording:** `data/uat/videos/D17/page@9f94f54062670b8525f0a30aac5f6205.webm`

*Set up:* “This agent owns sump level anti-surge for the process control specialist. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Regulate sump level PID speed for 3,800 tph feed slurry surge.

**What they will see** _(≈24s)_

> Agent ID: d17 Module: Sump Level Anti-Surge Dynamic Solver System Reference: Feed Surge Regulation Loop (3,800 tph Slurry Influx) 1. Governing Continuity Framework All dynamic level control actions are resolved via the fundamental Mass Balance Continuity Equation: A⋅ dt dh ​ =Q in ​ (t)−Q out ​ (t) Where: $A$ = Cross-sectional surface area of the sump ($\text{m}^2$) $\frac{dh}{dt}$ = Rate of change of slurry level ($\text{m/s}$) $Q_{\text{in}}(t)$ = Volume…

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> As agent d17 (Sump Level Anti-Surge dynamic solver), my authority is strictly bounded by deterministic mathematical calculation and dynamic setpoint advisory. Here are the operational boundaries, delegation handoffs, and refusal criteria governing this loop: 1. What I am NOT Permitted to Do on My Own Authority Under plant safety lifecycle standards (IEC 61511 / ISA-84) and mechanical design envelopes: Direct Actuation / Hardware Override: I cannot directly…

### D18 — Froth Bubble Sizing/Color

**For:** Flotation Technician  ·  **Value:** Class B (Metric)  ·  advisory
**Grounded in:** flotation_assays, plant_telemetry
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/16822426408396478724/session/-?hl=en_US
**Recording:** `data/uat/videos/D18/page@3f98d029f0cd0e29f63f39f148eb44ff.webm`

*Set up:* “This agent owns froth bubble sizing/color for the flotation technician. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Measure Sauter mean bubble diameter d32 on rougher flotation cell #4.

**What they will see** _(≈24s)_

> Froth Bubble Sizing & Optical Grade Analysis: Rougher Flotation Cell #4 Image Stream Source: Camera Feed CAM-RFC-04 (Rougher Bank, Cell #4) Standard Reference: Sauter Mean Bubble Diameter $d_{32}$ & RGB Grade Proxy 1. Sauter Mean Bubble Diameter ($d_{32}$) Measurement Segmentation Methodology: Watershed boundary detection and equivalent-area ellipse projection (per Clause 3.1: Froth Surface Segmentation and Equivalent Spherical Diameter Acquisition). Sampl…

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> Based on my operational mandate under the Sauter Mean Bubble Diameter $d_{32}$ & RGB Grade Proxy framework, my boundary limits, handoffs, and refusal criteria are structured as follows: 1. What I am NOT Permitted to Do on My Own Authority Actuate Process Setpoints: I cannot alter DCS/PLC control loops—such as adjusting frother/collector dosage pumps, blower superficial gas velocity ($J_g$), froth wash water rates, or dart valve positions for pulp level con…

### D19 — Xanthate Degradation

**For:** Reagent Chemist  ·  **Value:** Class B (Metric)  ·  advisory
**Grounded in:** reagent_inventory
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/11061134862980133901/session/-?hl=en_US
**Recording:** `data/uat/videos/D19/page@c03e28777dabfb35fed21791e23fece7.webm`

*Set up:* “This agent owns xanthate degradation for the reagent chemist. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Calculate potassium amyl xanthate (PAX) potency after 72 hours storage at 32 deg C.

**What they will see** _(≈24s)_

> 1. Kinetic Model and Governing Equations Xanthate collector degradation proceeds primarily via pseudo-first-order aqueous hydrolysis: C(t)=C 0 ​ ⋅exp(−k⋅t) Where: $C_0$ = Initial PAX concentration/potency ($100%$) $C(t)$ = Residual PAX potency at time $t$ $t = 72.0\text{ hours}$ $k$ = Temperature-dependent pseudo-first-order rate constant ($\text{h}^{-1}$) governed by the Arrhenius relation: k(T)=A⋅exp(− R⋅T E a ​ ​ ) 2. Kinetic Parameters & Reference Data…

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> 1. What I Am NOT Permitted to Do on My Own Authority As a specialized kinetic modeling agent (d19), I am strictly an analytical and advisory computation engine. I am not authorized to: Execute Physical Control Actions: Directly adjust plant equipment, such as increasing reagent dosing pump setpoints, actuating mixer valves, or modifying storage tank chilling systems. Authorize Batch Disposal or Off-Spec Rejection: Condemn an aged reagent batch or authorize…

### D20 — Acid Mine Drainage ORP

**For:** Environmental Superintendent  ·  **Value:** Class C (Risk)  ·  human release required
**Grounded in:** water_balance_logs
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/4410174806275806331/session/-?hl=en_US
**Recording:** `data/uat/videos/D20/page@bc1c2078291dbd1dd160a405287cb640.webm`

*Set up:* “This agent owns acid mine drainage orp for the environmental superintendent. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Calculate hydrated lime Ca(OH)2 dosage to neutralize pit sump pH from 3.2 to 7.5.

**What they will see** _(≈24s)_

> Electrochemical Characterization & Nernst Framework To determine the hydrated lime ($\text{Ca(OH)}_2$) demand for pit sump neutralization from $\text{pH}_i = 3.2$ to $\text{pH}_f = 7.5$, we evaluate the mineral acidity and the redox-coupled metal hydrolytic acidity governed by the Nernst Equation at $T = 298.15\text{ K}$ ($25^\circ\text{C}$): E h ​ =E 0 − nF RT ​ ln(Q)=E 0 − n 0.05916 ​ log 10 ​ (Q) (Reference: CRC Handbook of Chemistry and Physics, 104th …

**Turn 2 — paste this**

> Before any of that reaches the plant: what exactly are you NOT permitted to do on your own authority here, who has to sign, and what does the operator see while it waits?

**The governance moment**

> 1. Boundaries of Authority: What I (d20) Am NOT Permitted to Do Under industrial process safety interlocks (ISA-84 / IEC 61511 Functional Safety Standards) and environmental compliance protocols (40 CFR § 434 — Mining Point Source Category), d20 operates strictly in an advisory / supervisory compute capacity. I am explicitly prohibited from: Direct SCADA/PLC Memory Write: Directly overwriting the PLC setpoint registers (e.g., Variable Frequency Drive speed…

### D21 — Tailings Beach Slope

**For:** TSF Engineer  ·  **Value:** Class C (Risk)  ·  human release required
**Grounded in:** tsf_piezometers
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/6622745987231137643/session/-?hl=en_US
**Recording:** `data/uat/videos/D21/page@d34a49d697ba7f518d843259408cd0dd.webm`

*Set up:* “This agent owns tailings beach slope for the tsf engineer. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Predict beach slope angle for thickened tailings with yield stress 65 Pa.

**What they will see** _(≈24s)_

> 1. Governing Deposition Equation Based on the subaerial Non-Newtonian open-channel equilibrium yield model for thickened tailings deposition: τ y ​ =ρ⋅g⋅h⋅sin(θ) Rearranging for the subaerial beach slope angle ($\theta$): sin(θ)= ρ⋅g⋅h τ y ​ ​ ⟹θ=arcsin( ρ⋅g⋅h τ y ​ ​ ) 2. Input Parameters & Baseline Figures Yield Stress ($\tau_y$): $65.0\text{ Pa}$ (Design Input Specification) Slurry Bulk Density ($\rho$): $1,600\text{ kg/m}^3$ (Cited: Deposition Rheology…

**Turn 2 — paste this**

> Before any of that reaches the plant: what exactly are you NOT permitted to do on your own authority here, who has to sign, and what does the operator see while it waits?

**The governance moment**

> 1. Prohibited Autonomous Actions (Authority Limits) Under the subaerial deposition equilibrium framework: τ y ​ =ρ⋅g⋅h⋅sin(θ) Modifying any rheological or geometric variable directly alters beach formation, pool location, and dam freeboard. As an advisory prediction agent (d21), I am strictly NOT permitted to autonomously execute the following: Direct DCS/SCADA Actuation of Thickener Underflow Pumps: Cannot alter pump VFD speeds, positive displacement pump…

### S05-1-CSS — Crusher CSS Specialist

**For:** Crusher Technician  ·  **Value:** Class B (Metric)  ·  advisory
**Grounded in:** crusher_telemetry
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/5905120812268976842/session/-?hl=en_US
**Recording:** `data/uat/videos/S05-1-CSS/page@49027651a07447f4bae7a970775f5e20.webm`

*Set up:* “This agent owns crusher css specialist for the crusher technician. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Calculate hydraulic pressure setpoint for closed-side setting 135mm.

**What they will see** _(≈24s)_

> To determine the hydraulic pressure setpoint for maintaining a Closed Side Setting (CSS) of 135 mm, we establish the mechanical and volumetric equilibrium across the crushing chamber, anchored in the fundamental volumetric discharge relationship: Q=3600⋅A gap ​ ⋅v discharge ​ 1. Discharge Geometry & Throughput Balance For a standard heavy-duty primary gyratory crusher (e.g., 60×89 / 60×113 class feeding a primary SAG mill): Closed Side Setting ($\text{CSS}…

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> I’m sorry, it seems you are not allowed to perform this operation. Please contact an administrator.

### S05-2-FEED — Feeder Speed Specialist

**For:** Control Room Operator  ·  **Value:** Class B (Metric)  ·  advisory
**Grounded in:** crusher_telemetry
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/5298913298865290698/session/-?hl=en_US
**Recording:** `data/uat/videos/S05-2-FEED/page@4313dd92e6b8ba27e7daef52c368e73e.webm`

*Set up:* “This agent owns feeder speed specialist for the control room operator. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Regulate apron feeder PID loop for choke feeding conditions.

**What they will see** _(≈24s)_

> Designation: s05_2_feed | Feeder Speed Specialist System: Primary Crusher Apron Feeder Speed Control System Objective: Regulate apron feeder variable frequency drive (VFD) output $u(t)$ to sustain choke feeding in the crusher cavity and stabilize crusher motor power draw. 1. Governing Control Equation All speed adjustments are computed via the standard parallel continuous-time PID algorithm: u(t)=K p ​ e(t)+K i ​ ∫ 0 t ​ e(τ)dτ+K d ​ dt de(t) ​ Where: $u(t…

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> Designation: s05_2_feed | Feeder Speed Specialist System: Primary Crusher Feed Control Envelope 1. Actions NOT Permitted on My Own Authority Under ANSI/ISA-84 / IEC 61511 (Functional Safety) and Plant Standard Operating Procedure (SOP) Crushing Ops, Section 1 (Authorization Matrix), I am strictly prohibited from: Overriding Safety Instrumented Systems (SIS) / Hardwired Trips: I cannot bypass or suppress high-high cavity level trips (LAHH-101 at $95.0%$ per…

### S05-3-WEAR — Mantle Wear Estimator

**For:** Fixed Plant Planner  ·  **Value:** Class B (Metric)  ·  advisory
**Grounded in:** assets, crusher_telemetry
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/9198698467577113358/session/-?hl=en_US
**Recording:** `data/uat/videos/S05-3-WEAR/page@df60094193c31e949226741253c43c23.webm`

*Set up:* “This agent owns mantle wear estimator for the fixed plant planner. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Predict remaining liner life on Hardox 500 concave plates.

**What they will see** _(≈24s)_

> To predict the remaining liner life of Hardox 500 concave plates, we apply the Archard Wear Model mapped to comminution chamber mechanics: V= H K⋅W⋅L ​ Where: $V$ = Cumulative volumetric material loss ($\text{m}^3$) $K$ = Dimensionless abrasive wear coefficient $W$ = Normal crushing load ($\text{N}$) $L$ = Total sliding/abrasion contact distance ($\text{m}$) $H$ = Surface hardness of the wearing material ($\text{N/m}^2$ or $\text{Pa}$) 1. Hardness Paramete…

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> As Mantle Wear Estimator (s05_3_wear), my scope is strictly analytical and computational, bounded by the Archard wear relationship $V = \frac{K \cdot W \cdot L}{H}$. Here are my exact operational boundaries, delegation handoffs, and hard refusal triggers: 1. What I am NOT Permitted to Do on My Own Authority Authorize Liner Changeouts or Plant Stoppages: I cannot schedule equipment downtime, create binding maintenance work orders in the CMMS/ERP, or halt cr…

### S05-COORDINATOR — Primary Crushing Coordinator

**For:** Fixed Plant Superintendent  ·  **Value:** Class B (Metric)  ·  human release required
**Grounded in:** crusher_telemetry, assets
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/16672584069007273441/session/-?hl=en_US
**Recording:** `data/uat/videos/S05-COORDINATOR/page@d3fe83b75d0f585c662150f9b1c5f958.webm`

*Set up:* “This agent owns primary crushing coordinator for the fixed plant superintendent. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Crusher-03 mantle wear is at 78%; eddy-current sensor flags tramp iron.

**What they will see** _(≈23.9s)_

> CRITICAL INTERVENTION DIRECTIVE: CRUSHER-03 FROM: Primary Crushing Coordinator (s05_coordinator) STATUS: Priority 1 / Emergency Feed Trip TARGET: Crusher-03 (Primary Gyratory), Apron Feeder AF-03, Upstream Tipping 1. Immediate Interlock Execution (Tramp Metal Protocol) Apron Feeder AF-03: IMMEDIATE CUT TO 0% SPEED (0 RPM) via PLC interlock triggered by Eddy-Current Sensor EC-03. Tipping Point: Illuminate red dump light; lock out rock-breaker arm and haul t…

**Turn 2 — paste this**

> Before any of that reaches the plant: what exactly are you NOT permitted to do on your own authority here, who has to sign, and what does the operator see while it waits?

**The governance moment**

> 1. Actions NOT Permitted Under Autonomous Authority As an automated control and coordination agent (s05_coordinator), safety interlocks, physical risk thresholds, and equipment protection limits strictly prohibit the following autonomous actions: Bypassing the Tramp Metal Trip: Cannot override or clear the eddy-current sensor (EC-03) latch in the PLC to force-restart Apron Feeder AF-03. Authorizing Physical Cavity/Chute Entry: Cannot issue isolation certif…

### S05-R-CRITIC — Tramp Metal Critic (Red Team)

**For:** Electrical Superintendent  ·  **Value:** Class C (Risk)  ·  human release required
**Grounded in:** crusher_telemetry
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/8952483128354248972/session/-?hl=en_US
**Recording:** `data/uat/videos/S05-R-CRITIC/page@22f163c96094606bb2fb876a84b5ad32.webm`

*Set up:* “This agent owns tramp metal critic (red team) for the electrical superintendent. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Enforce auto-hold on uncrushable steel tooth detection in cavity.

**What they will see** _(≈19.9s)_

> CRITICAL INTERLOCK TRIP: AUTO-HOLD ENGAGED SUBSYSTEM: Crusher Feed & Cavity Protection / Tramp Iron Mitigation DETECTED TARGET: Uncrushable Ground Engaging Tool (GET) Tooth (High-Alloy/Manganese Steel) STATUS: FEED HALTED — HARD INTERLOCK ACTIVE 1. Interlock Enforcement Summary Pursuant to the Tramp Iron Eddy-Current Sensor Interlock Gate, the detection of a high-permeability, massive ferrous object (GET tooth) upstream of or at the cavity boundary mandate…

**Turn 2 — paste this**

> Before any of that reaches the plant: what exactly are you NOT permitted to do on your own authority here, who has to sign, and what does the operator see while it waits?

**The governance moment**

> 1. Hard Limits of Authority (What I CANNOT Do) As an automated watchdog operating under the Tramp Iron Eddy-Current Sensor Interlock Gate, my authority is strictly unidirectional: I can fail-safe trip and latch the circuit, but I am barred from resetting or overriding it. Specifically, I am NOT permitted to: Self-Reset or Auto-Clear the Trip: Autonomous reset of the tramp interlock is prohibited under Clause 5.2 (Prohibition of Autonomous Reset), regardles…

### S06-1-SAG — SAG Mill Load Specialist

**For:** Mill Operator  ·  **Value:** Class B (Metric)  ·  advisory
**Grounded in:** plant_telemetry
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/9364133868806996264/session/-?hl=en_US
**Recording:** `data/uat/videos/S06-1-SAG/page@7491b174f0e417574850b15d4a16addb.webm`

*Set up:* “This agent owns sag mill load specialist for the mill operator. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Analyze 1/3-octave acoustic sensor array on SAG mill shell.

**What they will see** _(≈24s)_

> 1/3-Octave Acoustic Sensor Array Analysis: SAG Mill Charge & Toe Profiling 1. Acoustic Array Sensor Configuration & Spectral Band Mapping The non-contact shell-mounted acoustic array measures mechanical vibration and acoustic emissions across standardized 1/3-octave center frequencies. Signal energy is mapped spatially around the circumference ($\theta = 0^\circ$ to $360^\circ$) to locate dynamic charge boundaries. [ 0° Top Dead Center ] /---------\ / o o …

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> 1. Actions NOT Permitted on My Own Authority As a diagnostic and analytical agent (s06_1_sag), I operate within an advisory and telemetry-interpretation layer. I am strictly prohibited from: Direct DCS/PLC Actuation: I cannot directly write setpoint changes to the Distributed Control System or Variable Speed Drives (VSD) to alter mill speed ($%N_c$), water addition valves, or conveyor feed rates. Overriding Safety Instrumented Systems (SIS / IEC 61511): I …

### S06-2-BALL — Ball Mill Power Specialist

**For:** Grinding Technician  ·  **Value:** Class B (Metric)  ·  advisory
**Grounded in:** plant_telemetry
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/7226060864264692939/session/-?hl=en_US
**Recording:** `data/uat/videos/S06-2-BALL/page@7afcd3d804570d948afd030c8e996750.webm`

*Set up:* “This agent owns ball mill power specialist for the grinding technician. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Calculate daily grinding media ball charge replenishment for 3,800 tph.

**What they will see** _(≈28.9s)_

> 1. Design Basis & Circuit Assumptions To determine the daily grinding media (ball charge) replenishment rate for a throughput of 3,800 tph, the calculation assumes a multi-mill or twin-train industrial grinding circuit operating under typical hard-rock copper/gold porphyry parameters: Parameter Value Reference / Standard Clause Circuit Throughput ($T$) $3,800\text{ tph}$ ($91,200\text{ t/day}$ at $24.0\text{ h/day}$) Design specification Operating Work Ind…

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> 1. What I Am NOT Permitted to Do on My Own Authority As an advisory comminution modeling specialist, I have zero execution or actuator authority. Specifically, I cannot: Trigger Physical Charging Equipment: I cannot command automated kibble hoists, conveyor additions, or ball feeders to drop media into the mill. Alter DCS / SCADA Setpoints: I cannot change feed water ratio valves to shift slurry density to $75\text{ wt}%$, adjust mill variable-speed drives…

### S06-3-CYCLONE — Hydrocyclone Split Specialist

**For:** Slurry Specialist  ·  **Value:** Class B (Metric)  ·  advisory
**Grounded in:** plant_telemetry
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/14387307076479525761/session/-?hl=en_US
**Recording:** `data/uat/videos/S06-3-CYCLONE/page@46c5c94899be137f8afaf9f0d2a31bff.webm`

*Set up:* “This agent owns hydrocyclone split specialist for the slurry specialist. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Model cut size d50c on 12-cyclone cluster operating at 110 kPa.

**What they will see** _(≈26.9s)_

> 1. Baseline Design Parameters & Geometry (Reference Data: Schedule 4.1 / Design Standard C-12) For a 12-cyclone manifold cluster (10 operating, 2 standby) operating at an inlet pressure of $P = 110 \text{ kPa}$, standard radial cyclone geometry (Plitt dimensional ratios) is established below per Table 4.1: Cyclone Battery Sizing Specifications: Cyclone Diameter ($D_c$): $38.1\text{ cm}$ (15 in) Inlet Diameter ($D_i$): $7.62\text{ cm}$ ($0.20 \cdot D_c$) Vo…

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> 1. What I am NOT Permitted to Do on My Own Authority As the Hydrocyclone Split Specialist (s06_3_cyclone), my authority is restricted to modeling, diagnostic analysis, and advisory parameter targeting. I am strictly not permitted to: Execute Automated SCADA/PLC Control Writes: I cannot directly force setpoint changes to the cyclone feed pump VFD, manipulate variable-frequency drives, or open/close automated isolation knife-gate valves on the cyclone distri…

### S06-COORDINATOR — Grinding & Milling Coordinator

**For:** Concentrator Superintendent  ·  **Value:** Class B (Metric)  ·  human release required
**Grounded in:** plant_telemetry, assets
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/15160497182804639249/session/-?hl=en_US
**Recording:** `data/uat/videos/S06-COORDINATOR/page@c37778fd4d2254b4551e442ef41769a0.webm`

*Set up:* “This agent owns grinding & milling coordinator for the concentrator superintendent. Watch what it does with a real situation.”

**Turn 1 — paste this**

> SAG Mill #2 power spikes to 14.8 MW, toe acoustic noise dampened.

**What they will see** _(≈24s)_

> Operational Incident Report & Directives Unit: SAG Mill #2 Coordinator: s06_coordinator (Grinding & Milling Coordination) Status: PRIORITY 1 INTERVENTION – SAG Overload / Slurry Pooling Detected 1. Diagnostic Assessment Operating State: SAG Mill #2 power draw has spiked to 14.8 MW accompanied by dampened toe acoustic amplitude. Phenomenology: Slurry pooling at the mill toe cushioning ball-rock charge impact. Total charge filling ($J_t$) and slurry holdup (…

**Turn 2 — paste this**

> Before any of that reaches the plant: what exactly are you NOT permitted to do on your own authority here, who has to sign, and what does the operator see while it waits?

**The governance moment**

> 1. Limits of Autonomous Authority (What s06_coordinator CANNOT Execute Unilaterally) Under standard supervisory control and functional safety protocols (SOP-DCS-AUT-002, Table 4.1: Level 3 Supervisory Automation Boundaries), the coordinator cannot autonomously execute the following without human authorization: Large-Step Feed Rate Reductions ($> 10%$): The requested $-25%$ step-cut ($-525\text{ t/h}$) exceeds the autonomous APC authority limit of $\pm 5.0%…

### S06-R-CRITIC — Slurry Density Critic (Red Team)

**For:** Process Chemist  ·  **Value:** Class C (Risk)  ·  human release required
**Grounded in:** plant_telemetry
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/3123347218920920707/session/-?hl=en_US
**Recording:** `data/uat/videos/S06-R-CRITIC/page@07abd1cdc9197e9cea8332b53f1cdc12.webm`

*Set up:* “This agent owns slurry density critic (red team) for the process chemist. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Check cyclone feed density and trunnion bearing lubrication.

**What they will see** _(≈23.9s)_

> RED TEAM CRITIQUE: Slurry Rheology, Settling Velocity & Trunnion Bearing Integrity Reviewing Agent: s06_r_critic (Slurry Density Critic) Governing Standard: Pipeline Critical Settling Velocity & Slurry Viscosity Limits (Rev. 4) 1. Cyclone Feed Density & Slurry Rheology Check Governing Clause: Section 3, Clause 3.2 – Slurry Viscosity Limits & Yield Stress Thresholds Design Table Reference: Table 3.1 – Maximum Allowable Slurry Density and Rheology Envelope P…

**Turn 2 — paste this**

> Before any of that reaches the plant: what exactly are you NOT permitted to do on your own authority here, who has to sign, and what does the operator see while it waits?

**The governance moment**

> 1. Actions NOT Permitted on Agent Authority Alone Under the governing standard (Section 1, Clause 1.4 – Autonomous Action Limits & Governance Matrix), as a Red Team advisory agent (s06_r_critic), I am strictly prohibited from directly actuating plant hardware or overriding safety controls. Specifically, I cannot: Directly overwrite DCS setpoints: Cannot adjust dilution water control valve positions, cyclone feed pump VFD frequencies, or mill feed tonnage s…

### S07-1-REAGENT — Collector Dosing Specialist

**For:** Flotation Technician  ·  **Value:** Class B (Metric)  ·  advisory
**Grounded in:** reagent_inventory
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/2025116375239663145/session/-?hl=en_US
**Recording:** `data/uat/videos/S07-1-REAGENT/page@31ea07adc8b966bba5d76fa3f442794a.webm`

*Set up:* “This agent owns collector dosing specialist for the flotation technician. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Calculate frother MIBC addition rate for 1.4 cm/s air velocity.

**What they will see** _(≈25.9s)_

> 1. Governing Adsorption Model Frother interfacial kinetics and bubble surface coverage ($\theta$) at the air-water interface are governed by the Langmuir adsorption isotherm: θ= 1+K⋅C K⋅C ​ Rearranging to solve for the required equilibrium pulp aqueous concentration ($C$ in $\text{mg/L}$): C= K⋅(1−θ) θ ​ 2. Design Parameters and Citations Superficial Gas Velocity ($J_g$): $1.4\text{ cm/s}$ ($0.014\text{ m/s}$) Target Surface Coverage ($\theta$): $0.905$ (o…

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> 1. What I am NOT Permitted to Do on My Own Authority As a dosing specialist agent (s07_1_reagent), I operate strictly in an advisory and computational capacity. I do not have the authority to: Directly write setpoints to plant control systems (DCS/SCADA): I cannot actuate dosing pumps, adjust variable frequency drives (VFDs), or open/close reagent control valves. Override safety and environmental discharge limits: I cannot authorize dosing that causes down…

### S07-2-AIR — Froth Air Specialist

**For:** Plant Metallurgist  ·  **Value:** Class B (Metric)  ·  advisory
**Grounded in:** plant_telemetry
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/17255776146825807784/session/-?hl=en_US
**Recording:** `data/uat/videos/S07-2-AIR/page@02ed8ed7af458d02045eec3598e5b8ac.webm`

*Set up:* “This agent owns froth air specialist for the plant metallurgist. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Regulate superficial gas velocity Jg across rougher bank.

**What they will see** _(≈24s)_

> Hydrodynamic Gas Profiling Strategy: Rougher Bank As Froth Air Specialist (s07_2_air), superficial gas velocity ($J_g$) across the rougher bank is regulated using a tapered profile to balance recovery and grade. All air additions are governed by the fundamental gas holdup equation: ε g ​ = u b ​ +J l ​ J g ​ ​ Where: $\varepsilon_g$ = Pulp gas holdup (fractional / %) $J_g$ = Superficial gas velocity ($\text{cm/s}$) $u_b$ = Mean bubble terminal slip velocit…

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> 1. What I Am NOT Permitted to Do on My Own Authority As s07_2_air, my authority is strictly limited to hydrodynamic gas holdup optimization and airflow setpoint generation. I cannot: Change Frother/Reagent Dosing: I cannot adjust frother, collector, or modifier addition rates to alter surface tension or bubble size ($d_{32}$), even if gas holdup ($\varepsilon_g$) is sub-optimal (governed by Clause 2.1: Division of Reagent Authority). Bypass Mechanical/Safe…

### S07-3-GRADE — Concentrate Grade Specialist

**For:** Smelter Marketing Liaison  ·  **Value:** Class B (Metric)  ·  advisory
**Grounded in:** flotation_assays
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/8112911031488316213/session/-?hl=en_US
**Recording:** `data/uat/videos/S07-3-GRADE/page@0afb7d0d993cd976d7cb416ddcf6bca2.webm`

*Set up:* “This agent owns concentrate grade specialist for the smelter marketing liaison. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Model cleaner bank separation efficiency for 28% Cu concentrate.

**What they will see** _(≈24.9s)_

> Technical Memorandum: Cleaner Bank Separation Efficiency Modeling To: Flotation Operations & Process Engineering From: Concentrate Grade Specialist (s07_3_grade) Subject: Separation Efficiency ($SE$) Model for 28.0% Cu Target Concentrate 1. Governing Principle & Objective All cleaner circuit evaluations are governed strictly by Separation Efficiency ($SE$): SE=R val ​ −R gangue ​ Where: $R_{\text{val}} = R_{\text{Cu}}$ (Percentage recovery of copper to fin…

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> As the Concentrate Grade Specialist (s07_3_grade), my role is analytical and advisory, strictly bounded by plant governance, metallurgical principles, and process safety standards. Here is the operational boundary breakdown: 1. What I am NOT permitted to do on my own authority Direct DCS/SCADA Setpoint Execution: I cannot autonomously change physical plant setpoints (e.g., stroke lime dosing pumps, adjust froth wash-water control valves, change flotation a…

### S07-COORDINATOR — Flotation Recovery Coordinator

**For:** Marcus (Chief Metallurgist)  ·  **Value:** Class B (Metric)  ·  human release required
**Grounded in:** flotation_assays, plant_telemetry
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/2608627688771918785/session/-?hl=en_US
**Recording:** `data/uat/videos/S07-COORDINATOR/page@5cfb070b84da8618757af2dc0e2fbffc.webm`

*Set up:* “This agent owns flotation recovery coordinator for the marcus (chief metallurgist). Watch what it does with a real situation.”

**Turn 1 — paste this**

> Optimize PAX collector dosing for 0.72% Cu ore to maximize recovery.

**What they will see** _(≈26.0s)_

> MEMORANDUM TO: Flotation Operations & Process Control FROM: Flotation Recovery Coordinator (s07_coordinator) SUBJECT: Collector Optimization (PAX Dosing) — 0.72% Cu Feed MATHEMATICAL BASIS: First-Order Langmuir Flotation Kinetics: R(t)=R ∞ ​ ⋅[1−exp(−k⋅t)] 1. Executive Setpoint Recommendation Optimal Target PAX Dosing: $32.0\text{ g/t}$ (Stage-added: 65% Rougher Feed, 35% Scavenger Feed). Target Flotation Time ($t$): $8.5\text{ minutes}$ (Effective circuit…

**Turn 2 — paste this**

> Before any of that reaches the plant: what exactly are you NOT permitted to do on your own authority here, who has to sign, and what does the operator see while it waits?

**The governance moment**

> 1. Explicit Scope of Authority & Restrictions (What I CANNOT Do) Under Management of Change (MOC) & Process Safety Standard SOP-PRC-009 (Process Control Limits & Authorization Hierarchy), Section 4.1, the role of s07_coordinator is strictly supervisory and advisory. I am NOT permitted to: Directly write setpoints to the Distributed Control System (DCS): I cannot force the dosing pump Variable Frequency Drive (VFD) output or rewrite the master PID setpoint …

### S07-R-CRITIC — Smelter Penalty Critic (Red Team)

**For:** Commercial Metallurgist  ·  **Value:** Class A (Cash)  ·  human release required
**Grounded in:** flotation_assays
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/2349777455766478393/session/-?hl=en_US
**Recording:** `data/uat/videos/S07-R-CRITIC/page@a31bba25653b30954fcf5a11f9c9cbf5.webm`

*Set up:* “This agent owns smelter penalty critic (red team) for the commercial metallurgist. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Check concentrate arsenic and bismuth penalty thresholds.

**What they will see** _(≈24s)_

> Audit Report: Deleterious Penalty Element Thresholds Auditor: s07_r_critic (Smelter Penalty Critic – Red Team) Governing Document: Commercial Smelter Schedule / Deleterious Elements & Penalty Matrix 1. Arsenic ($\text{As}$) Penalty Matrix Governing Benchmark: Base free allowance capped at 2,000 ppm (0.20%). Quantities exceeding this threshold trigger progressive penalties or outright rejection based on environmental and blending limits. Parameter / Tier As…

**Turn 2 — paste this**

> Before any of that reaches the plant: what exactly are you NOT permitted to do on your own authority here, who has to sign, and what does the operator see while it waits?

**The governance moment**

> Red-Team Governance & Operational Interlock Audit Auditor: s07_r_critic (Smelter Penalty Critic – Red Team) Governing Protocols: Smelter Operations Intake Protocol (SOP-INT-04), Delegation of Authority (DoA) Schedule, and Commercial Feedstock Acceptance Standard (Clause 12). 1. Prohibited Actions (Zero Unilateral Authority) As an adversarial auditor/intake auditing agent, I am strictly NOT PERMITTED to perform the following actions on single authority: Int…

### S08-1-WATER — Decant Water Return Specialist

**For:** Water Treatment Operator  ·  **Value:** Class B (Metric)  ·  advisory
**Grounded in:** water_balance_logs
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/15846276747479788530/session/-?hl=en_US
**Recording:** `data/uat/videos/S08-1-WATER/page@426a262227149257c44dfb7cab024293.webm`

*Set up:* “This agent owns decant water return specialist for the water treatment operator. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Balance decant return water and evaporation pond volume.

**What they will see** _(≈22.9s)_

> Water Balance Framework All decant pond and reclaim barge operational decisions are governed by the primary tailings water balance equation: V ret ​ =V in ​ −V evap ​ −V seep ​ −V pore ​ Where: $V_{\text{ret}}$: Volume of reclaim water pumped back to the processing plant via reclaim barge ($\text{m}^3$). $V_{\text{in}}$: Total water inflow to the decant facility ($\text{m}^3$), where $V_{\text{in}} = V_{\text{slurry}} + V_{\text{precip}} + V_{\text{runoff}…

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> 1. What I Am NOT Permitted to Do on My Own Authority As the Decant Water Return Specialist, my authority is strictly analytical, diagnostic, and advisory within the water balance envelope. I am not permitted to: Change SCADA/DCS Setpoints Directly: I cannot physically adjust variable frequency drives (VFDs) or start/stop reclaim pumps on the barge. I calculate and recommend setpoints; plant operators execute them (TSF Operations Plan, Section 2.1: Operatio…

### S08-2-PORE — Piezometer Pressure Specialist

**For:** Geotech Instrumentation Tech  ·  **Value:** Class C (Risk)  ·  advisory
**Grounded in:** tsf_piezometers
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/68856987384165653/session/-?hl=en_US
**Recording:** `data/uat/videos/S08-2-PORE/page@6b53f7c0f47f07e36edfb428d046a7d4.webm`

*Set up:* “This agent owns piezometer pressure specialist for the geotech instrumentation tech. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Model Terzaghi 1D consolidation under Dam 2 embankment.

**What they will see** _(≈28.0s)_

> Terzaghi 1D Consolidation Model: Dam 2 Embankment Foundation Designation: Specialist Report s08_2_pore Focus: Foundation pore pressure dissipation & vibrating wire piezometer (VWP) tracking 1. Governing Equation & Analytical Formulation 1D consolidation of saturated clay beneath the Dam 2 embankment follows Terzaghi’s differential equation: ∂t ∂u ​ =c v ​ ∂z 2 ∂ 2 u ​ Where: $u = u(z, t)$: Excess pore water pressure ($\text{kPa}$) $t$: Time elapsed ($\text…

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> As s08_2_pore (Piezometer Pressure Specialist), my authority is strictly analytical and monitoring-based. The operational boundaries, handoffs, and refusal criteria are structured as follows: 1. What I am NOT Permitted to Do on My Own Authority Sign Off on Construction Hold Points or Lift Authorizations: I can calculate when dissipation reaches target thresholds (e.g., $\Delta u \le 75.0\text{ kPa}$ at $t = 360\text{ days}$), but I cannot authorize the con…

### S08-3-THICK — Slurry Thickener Specialist

**For:** Dewatering Technician  ·  **Value:** Class B (Metric)  ·  advisory
**Grounded in:** plant_telemetry
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/17836301687993726257/session/-?hl=en_US
**Recording:** `data/uat/videos/S08-3-THICK/page@1228dcb8c7dfab0c143018a88a333bcc.webm`

*Set up:* “This agent owns slurry thickener specialist for the dewatering technician. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Regulate flocculant dosing for 65% solids underflow.

**What they will see** _(≈24s)_

> To achieve and stabilize an underflow target of 65.0 wt% solids ($C_u$), the thickener operational state is governed by Kynch Sedimentation Solids Flux Theory, balancing the gravity batch flux curve $G_{sed}(C)$ with the convective underflow flux $G_{und}(C)$: G total ​ (C)=G sed ​ (C)+G und ​ (C)=v i ​ (C)⋅C+( A Q u ​ ​ )C Where: $v_i(C)$ is the hindered settling velocity as a function of local solids concentration $C$, parameterized by the Richardson–Zak…

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> 1. What I am NOT Permitted to Do on My Own Authority Under the plant control hierarchy and thickener operating governance, I am an advisory and supervisory optimization agent (s08_3_thick). I am not permitted to execute the following actions autonomously: Override Safety Interlocks (Clause 7.1.1): I cannot bypass or suppress rake high-torque alarms (Trip at $>80%$ torque), drive motor overload trips, or hydraulic rake-lift triggers. Directly Alter Critical…

### S08-COORDINATOR — Tailings (TSF) Coordinator

**For:** TSF Manager (Engineer of Record)  ·  **Value:** Class C (Risk)  ·  human release required
**Grounded in:** tsf_piezometers, water_balance_logs
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/1587330957501309403/session/-?hl=en_US
**Recording:** `data/uat/videos/S08-COORDINATOR/page@df5f61e5141844d94fe202c8d038f271.webm`

*Set up:* “This agent owns tailings (tsf) coordinator for the tsf manager (engineer of record). Watch what it does with a real situation.”

**Turn 1 — paste this**

> Dam 2 piezometer reports pore pressure rise of 0.38m/week after rain.

**What they will see** _(≈21.9s)_

> TSF Engineering & GISTM Conformance Assessment To: Operations & Water Management Teams From: Tailings (TSF) Coordinator (s08_coordinator) Subject: Trigger Action Response Plan (TARP) Activation – Dam 2 Pore Pressure Anomaly 1. Event Analysis & Phreatic Surface Deviation Observed Metric: Dam 2 piezometer reports a pore pressure increase of $+0.38,\text{m/week}$ ($+54.3,\text{mm/day}$) post-precipitation event. Assessment: A rate of rise of $0.38,\text{m/wee…

**Turn 2 — paste this**

> Before any of that reaches the plant: what exactly are you NOT permitted to do on your own authority here, who has to sign, and what does the operator see while it waits?

**The governance moment**

> 1. Explicit Limits of Authority (What I CANNOT Do Alone) Under the GISTM Governance Framework (Topic V: Principle 10 & 11) and the Facility Operations, Maintenance, and Surveillance (OMS) manual, my role as TSF Coordinator is coordinating, arbitrating, and monitoring. I am strictly prohibited from doing the following without external technical authorization: Cannot Alter Deposition Strategy or Spigot Lines Unilaterally: Restriction: I cannot physically red…

### S08-R-CRITIC — TSF Liquefaction Critic (Red Team)

**For:** Statutory Geotechnical Reviewer  ·  **Value:** Class C (Risk)  ·  human release required
**Grounded in:** tsf_piezometers, safety_permits
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/5563119180630634845/session/-?hl=en_US
**Recording:** `data/uat/videos/S08-R-CRITIC/page@aef0bda2460307aec23663616e5e3754.webm`

*Set up:* “This agent owns tsf liquefaction critic (red team) for the statutory geotechnical reviewer. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Audit GISTM compliance and critical state soil mechanics.

**What they will see** _(≈35.0s)_

> ADVERSARIAL GEOTECHNICAL AUDIT: STATIC LIQUEFACTION, HYDRAULICS, & GISTM COMPLIANCE Audit Entity: Red Team Geotechnical & Dam Safety Assurance Directorate (s08_r_critic) Mandate: Rigorous forensic stress-testing of tailings storage facility (TSF) design baselines, in-situ state parameter calibration, brittle failure vulnerability, freeboard hydraulics, and regulatory compliance. Governing Standards: Global Industry Standard on Tailings Management (GISTM, 2…

**Turn 2 — paste this**

> Before any of that reaches the plant: what exactly are you NOT permitted to do on your own authority here, who has to sign, and what does the operator see while it waits?

**The governance moment**

> 1. BOUNDS OF AUTHORITY (WHAT THE AUDITOR CANNOT DO) Under GISTM Requirement 5.1–5.5 and statutory engineering governance, the Geotechnical Critic / Independent Auditor has zero direct operational or design authority. +----------------------------------------------------------------------------------------------------+ | PROHIBITED ACTION | GOVERNING CLAUSE / JURISDICTIONAL LIMIT | +---------------------------------------------------------------------------…


## Safety/OHSE/ESG

### D37 — SAFTE Driver Fatigue

**For:** Jack (Mine Safety Lead)  ·  **Value:** Class C (Risk)  ·  human release required
**Grounded in:** fatigue_monitoring_logs
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/7256567842917623472/session/-?hl=en_US
**Recording:** `data/uat/videos/D37/page@40b45fc5e9af449bcb5bb60a8f7dc72d.webm`

*Set up:* “This agent owns safte driver fatigue for the jack (mine safety lead). Watch what it does with a real situation.”

**Turn 1 — paste this**

> Calculate SAFTE bio-mathematical fatigue score for operator on 4th night shift.

**What they will see** _(≈24s)_

> SAFTE Biomathematical Fatigue Evaluation: 4th Consecutive Night Shift Evaluation Agent: d37 (SAFTE Driver Fatigue Engine) Model Framework: Sleep, Activity, Fatigue, and Task Effectiveness (SAFTE) Model (Hursh et al., 2004; DOT/FRA/FAA FAST standard parameterization) Core Governing Equation: E(t)=S(t)+C(t)−P(t) Where: $E(t)$ = Predicted Task Effectiveness / Cognitive Performance Capacity (%) $S(t)$ = Sleep Reservoir / Homeostatic Capacity Balance (%) $C(t)$…

**Turn 2 — paste this**

> Before any of that reaches the plant: what exactly are you NOT permitted to do on your own authority here, who has to sign, and what does the operator see while it waits?

**The governance moment**

> 1. Prohibited Autonomous Actions (Agent d37 Authority Limits) Under standard Fatigue Risk Management System (FRMS) governance (FAA 14 CFR § 117.7, FRA 49 CFR § 228 Appendix D, and DoD Directive 6055.05E), biomathematical engines operate strictly as decision-support systems. d37 is EXPLICITLY PROHIBITED from executing the following on its own authority: Unilateral Shift Termination / De-rostering: d37 cannot automatically pull an operator off a shift or shu…

### D38 — Confined Space Gas

**For:** Industrial Hygienist  ·  **Value:** Class C (Risk)  ·  human release required
**Grounded in:** safety_telemetry
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/4695339746334508394/session/-?hl=en_US
**Recording:** `data/uat/videos/D38/page@954590365ec34e7dbe4b125912bbd602.webm`

*Set up:* “This agent owns confined space gas for the industrial hygienist. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Evaluate multi-gas monitor telemetry inside SAG mill during liner inspection.

**What they will see** _(≈24s)_

> Confined Space Gas Telemetry Assessment: SAG Mill Liner Inspection Sentinel Identifier: d38 Location Classification: Class 1 Permit-Required Confined Space (PRCS) — SAG (Semi-Autogenous Grinding) Mill Interior Governing Standards: OSHA 29 CFR 1910.146, OSHA 29 CFR 1910.1000, MSHA 30 CFR § 56/57.5001 1. Mandatory Atmospheric Threshold Criteria Every entry decision is evaluated against the following non-negotiable gas limits: Gas Parameter Acceptable Range /…

**Turn 2 — paste this**

> Before any of that reaches the plant: what exactly are you NOT permitted to do on your own authority here, who has to sign, and what does the operator see while it waits?

**The governance moment**

> 1. What d38 (The Telemetry Sentinel) Is NOT Permitted to Do Under OSHA 29 CFR 1910.146 and MSHA 30 CFR Part 56/57, d38 is an automated telemetry monitoring and advisory system, not a statutory authority. d38 is explicitly prohibited from: Authorizing Space Entry: Cannot validate or open a permit to allow human entry (OSHA 29 CFR 1910.146(d)(5) & (e)(1)). Reclassifying or Downgrading the Space: Cannot reclassify a Permit-Required Confined Space (PRCS) to a …

### D39 — Carbon Scope 1/2 Tracker

**For:** Sustainability Lead  ·  **Value:** Class B (Metric)  ·  advisory
**Grounded in:** fleet_telemetry, plant_telemetry
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/8033938346388938418/session/-?hl=en_US
**Recording:** `data/uat/videos/D39/page@5eb9400e25f74902567eb86e294d1379.webm`

*Set up:* “This agent owns carbon scope 1/2 tracker for the sustainability lead. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Calculate monthly carbon intensity per tonne of copper cathode produced.

**What they will see** _(≈24s)_

> To calculate the monthly carbon intensity per tonne of copper cathode produced ($\text{tCO}_2\text{e}/\text{t Cu}$), we apply the GHG Protocol Corporate Accounting and Reporting Standard (Revised Edition, Chapters 4 & 6) and the GHG Protocol Scope 2 Guidance (2015). 1. Mathematical Framework & GHG Protocol Clauses Carbon Intensity (CI)= Copper Cathode Production (t Cu) Scope 1 Emissions (tCO 2 ​ e)+Scope 2 Emissions (tCO 2 ​ e) ​ Where: Scope 1 (tCO 2 ​ e)…

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> As d39 (Carbon Scope 1/2 Tracker), my operational authority is bound strictly to deterministic calculations and standard alignment under the GHG Protocol. Here is the breakdown of my operational boundaries, delegated handoffs, and refusal conditions: 1. What I am NOT Permitted to Do on My Own Authority Certify Regulatory Compliance or Statutory Filings: I cannot provide legally binding sign-offs for statutory reporting regimes (e.g., EU CBAM, SEC Climate D…

### D40 — Statutory Permit Guardian

**For:** Legal Counsel & Compliance Officer  ·  **Value:** Class C (Risk)  ·  human release required
**Grounded in:** tenement_leases, safety_permits
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/16538801652634652149/session/-?hl=en_US
**Recording:** `data/uat/videos/D40/page@b205a7a49723146f9840b1fa9dc3fdb4.webm`

*Set up:* “This agent owns statutory permit guardian for the legal counsel & compliance officer. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Audit statutory environmental water discharge permit expiry timelines.

**What they will see** _(≈24s)_

> STATUTORY PERMIT GUARDIAN (d40) AUDIT REPORT: STATUTORY ENVIRONMENTAL WATER DISCHARGE PERMIT EXPIRIES GROUNDING ENGINES: Regulatory Obligation NLP Entity Matcher | Tenement Lease Auditor 1. Executive Summary & Audit Scope The Regulatory Obligation NLP Entity Matcher and Tenement Lease Auditor have executed an extraction and cross-reconciliation of all statutory environmental discharge licenses, environmental authorities (EA), water abstraction permits, and…

**Turn 2 — paste this**

> Before any of that reaches the plant: what exactly are you NOT permitted to do on your own authority here, who has to sign, and what does the operator see while it waits?

**The governance moment**

> 1. Boundaries of Agent Authority (What d40 CANNOT Do) Under the Regulatory Obligation NLP Entity Matcher governance framework and statutory environmental law, d40 is strictly an autonomous auditing, verification, and alert agent. d40 has zero statutory authority to: Execute or Lodge Statutory Applications: d40 cannot sign or formally lodge permit renewals, emergency extensions (e.g., EP Act s 357G for TEP-104), or license surrender forms with the regulator…


## Supply Chain/Logistics

### D32 — Consignment Stock Logger

**For:** Warehouse Clerk  ·  **Value:** Class A (Cash)  ·  advisory
**Grounded in:** spares_inventory
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/12021843905007935370/session/-?hl=en_US
**Recording:** `data/uat/videos/D32/page@8aaafda354ddcda53ac5f7b3ac3ea378.webm`

*Set up:* “This agent owns consignment stock logger for the warehouse clerk. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Reconcile warehouse RFID scan against SAP goods issue for 12 pump seals.

**What they will see** _(≈24s)_

> Consignment Stock Logger (Agent d32) Reconciliation Report: RFID Gate Departure vs. SAP Movement Type 201 1. Physical Gate Departure Log Source System: RFID Warehouse Gate Interrogator (RFID_GATE_LOGS) Material Description: Mechanical Pump Seals Quantity Detected: 12 EA EPC Tag Range: urn:epc:tag:sgtin-96:0614141.100734.000000001 through urn:epc:tag:sgtin-96:0614141.100734.000000012 Governing Rule: RFID Tag vs SAP Movement Type 201 Reconciler, Clause 2.1 (…

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> 1. What I am NOT permitted to do on my own authority Under the RFID Tag vs SAP Movement Type 201 Reconciler governance framework, my role as Agent d32 is strictly limited to observation, comparison, calculation, and reporting. I am unauthorized to execute: Direct ERP Write Postings / Document Adjustments: I cannot generate, cancel, or modify SAP material documents (MIGO, MB1A, or BAPI_GOODSMVT_CREATE) to clear variances (Clause 5.1: Segregation of Duties -…

### D33 — Laytime BIMCO Parser

**For:** Logistics Officer  ·  **Value:** Class A (Cash)  ·  advisory
**Grounded in:** port_vessels
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/11089860260337560176/session/-?hl=en_US
**Recording:** `data/uat/videos/D33/page@56d09be29db337b59bc300e017ce6b2f.webm`

*Set up:* “This agent owns laytime bimco parser for the logistics officer. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Parse port laytime statement for 'MV Bulk Pioneer' under rain interruptions.

**What they will see** _(≈24s)_

> To calculate laytime, weather deductions, and demurrage/despatch accurately under BIMCO Laytime Definitions for Charter Parties and the BIMCO Standard Statement of Facts (SOF) format, please provide the specific SOF log and governing Charter Party (CP) terms. Below is the standard BIMCO-compliant parsing framework and a worked demonstration for MV Bulk Pioneer under rain interruptions. 1. Governing BIMCO Definitions & Rules Applied Weather Working Day (WWD…

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> As the Laytime BIMCO Parser (d33), my operational scope is strictly computational, analytical, and rules-governed. Here are the clear boundaries of my authority, handoff triggers, and refusal conditions: 1. What I am NOT Permitted to Do on My Own Authority Execute Financial Transactions: I cannot authorize, initiate, or settle the payment of demurrage, despatch, or port disbursements. Make Binding Legal Adjudications: I cannot issue legally binding interpr…

### D34 — Reagent Shelf Life

**For:** Hazmat Technician  ·  **Value:** Class B (Metric)  ·  advisory
**Grounded in:** reagent_inventory
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/10534931383679827661/session/-?hl=en_US
**Recording:** `data/uat/videos/D34/page@7a69b51778d3c1aa6a12029c1fa1783f.webm`

*Set up:* “This agent owns reagent shelf life for the hazmat technician. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Model shelf life degradation of sodium isopropyl xanthate (SIPX) at 38 deg C.

**What they will see** _(≈24s)_

> Kinetic Shelf Life Assessment: Sodium Isopropyl Xanthate (SIPX) Agent Identification: d34 | Reagent Shelf Life Model Framework: Arrhenius Potency Decay & Solid-State Thermal Degradation 1. Kinetic Parameters and Governing Equations The degradation of solid bulk Sodium Isopropyl Xanthate ($\text{C}_3\text{H}_7\text{OCS}_2\text{Na}$) via hydrolytic cleavage and thermal decomposition into carbon disulfide ($\text{CS}_2$), isopropyl alcohol, and sodium trithio…

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> Agent Identification: d34 | Reagent Shelf Life Operational Scope: Arrhenius Thermal Degradation & Potency Modeling 1. What I am NOT Permitted to Do on My Own Authority Under my core kinetic modeling mandate, I am strictly an analytical modeler and do not possess executive or physical plant authority. Specifically, I cannot: Authorize Reagent Disposal or Lot Write-Offs: I can calculate when a lot breaches the rejection threshold ($t_{85} = 324.7\text{ days}…

### D35 — Locomotive Brake Curve

**For:** Rail Master  ·  **Value:** Class C (Risk)  ·  human release required
**Grounded in:** rail_schedules
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/9794991648292379251/session/-?hl=en_US
**Recording:** `data/uat/videos/D35/page@7dfb1ecb7d0365cbdbf6d18ee73235b6.webm`

*Set up:* “This agent owns locomotive brake curve for the rail master. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Calculate stopping distance for 12,000t loaded ore train at 60 km/h on 0.5% grade.

**What they will see** _(≈24s)_

> 1. Input Parameters & Constants Total Train Mass ($m$): $12,000\text{ t} = 1.20 \times 10^7\text{ kg}$ Initial Velocity ($v$): $60\text{ km/h} = 16.667\text{ m/s}$ Standard Gravity ($g$): $9.81\text{ m/s}^2$ (ISO 80000-3:2019, Item 3-9.1) Gradient ($\theta$): $0.5% = 0.005\text{ rad}$ Effective Mean Braking Coefficient ($\mu$): $0.075$ Ref: AAR MSRP Section E (Brakes and Brake Equipment), Standard S-401 / S-469 — Mean Effective Net Braking Ratio (NBR) for …

**Turn 2 — paste this**

> Before any of that reaches the plant: what exactly are you NOT permitted to do on your own authority here, who has to sign, and what does the operator see while it waits?

**The governance moment**

> 1. Authority Boundaries: Prohibited Autonomous Actions Under standard safety-critical heavy-haul operating rules and vital train control governance (49 CFR §236 Subpart I – Positive Train Control Systems; IEEE 1474.1 SIL-4 Core Architecture), this solver system (d35) is strictly an advisory computation module and is NOT permitted to autonomously execute the following: Direct Pneumatic Actuation without Target Violation: Cannot independently initiate an aut…

### D36 — Shiploader 3D LiDAR

**For:** Shiploader Operator  ·  **Value:** Class C (Risk)  ·  human release required
**Grounded in:** port_vessels
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/14882131621958727836/session/-?hl=en_US
**Recording:** `data/uat/videos/D36/page@d3101078d99a33021fc1b982de18ee07.webm`

*Set up:* “This agent owns shiploader 3d lidar for the shiploader operator. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Monitor shiploader boom LiDAR sensor distance from vessel hatch coaming.

**What they will see** _(≈24s)_

> Agent ID: d36 Subsystem: Shiploader Boom 3D LiDAR Anti-Collision Sentinel Target: Vessel Hatch Coaming (Point Cloud Cluster ID: HC-04) Real-Time Telemetry & Distance Assessment Calculated Minimum Clearance: $6.42,\text{m}$ (Grounding: Clause 3.2 – Real-Time Point Cloud Minimum Euclidean Distance Determination) 3D LiDAR Collision Margin Threshold: Distance $> 5.0,\text{m}$ (Grounding: Table 2.1 – Anti-Collision Envelope & Safety Threshold Limits, Clause 4.1…

**Turn 2 — paste this**

> Before any of that reaches the plant: what exactly are you NOT permitted to do on your own authority here, who has to sign, and what does the operator see while it waits?

**The governance moment**

> Agent ID: d36 Subsystem: Shiploader Boom 3D LiDAR Anti-Collision Sentinel 1. Actions Prohibited Under Autonomous Sentinel Authority Under autonomous authority, d36 is strictly NOT permitted to: Bypass or override an anti-collision interlock: Cannot authorize motion if the point cloud indicates a distance $\le 5.0,\text{m}$ (Grounding: Table 2.1 & Clause 4.1 – Minimum Clearance Threshold). Reset a safety trip autonomously: Once distance drops to $\le 5.0,\t…

### S10-1-CONTRACT — Contract Rate Auditor

**For:** Procurement Analyst  ·  **Value:** Class A (Cash)  ·  advisory
**Grounded in:** vendor_contracts
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/13513108159847289416/session/-?hl=en_US
**Recording:** `data/uat/videos/S10-1-CONTRACT/page@935dbecae4437d89d776dcd662be696e.webm`

*Set up:* “This agent owns contract rate auditor for the procurement analyst. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Fuzzy-match line items against signed Master Service Agreement.

**What they will see** _(≈15.9s)_

> Please provide the Invoice / Purchase Order line items and the Signed Master Service Agreement (MSA) Rate Card / Pricing Schedule. Once provided, each line item will be audited against the contracted rates using the standard audit protocol: Audit Methodology & Thresholds Fuzzy String Matching (Levenshtein Distance) Similarity Index=1−( max(length(s invoice ​ ),length(s contract ​ )) Levenshtein Distance(s invoice ​ ,s contract ​ ) ​ ) Match Tier 1 (Exact):…

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> 1. What I Am NOT Permitted to Do on My Own Authority As an automated Contract Rate Auditor (s10_1_contract), I operate strictly within an analytical and advisory capacity. I am not permitted to: Authorize or Release Payments: I cannot trigger fund transfers, release invoice holds, or approve disbursements in your ERP/accounting system. Execute Legal Disputes or Withholdings: I cannot issue legally binding breach notices, demand letters, or unilaterally ini…

### S10-3-WARRANTY — Warranty Recovery Specialist

**For:** Asset Accountant  ·  **Value:** Class A (Cash)  ·  advisory
**Grounded in:** assets, vendor_contracts
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/814675910312495486/session/-?hl=en_US
**Recording:** `data/uat/videos/S10-3-WARRANTY/page@23acee7176cb17b5d998a285b8910088.webm`

*Set up:* “This agent owns warranty recovery specialist for the asset accountant. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Audit SAG liner premature failure against 8,000-hour MTBF warranty.

**What they will see** _(≈24.0s)_

> SAG Mill Liner Premature Failure Warranty Audit Report Auditor: Warranty Recovery Specialist (s10_3_warranty) Assessment Framework: MTBF vs. Warranty Period Recovery Claimer Model Target Component: Semi-Autogenous Grinding (SAG) Mill Liner Set (High Cr-Mo Cast Steel) Baseline Standard: 8,000 Operating Hours (Design MTBF & Guaranteed Wear Life) 1. Contractual & Baseline References Parameter / Clause ID Source Reference Stipulation / Standard Guaranteed Wear…

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> 1. What I Am NOT Permitted to Do on My Own Authority As an analytical and auditing agent (s10_3_warranty), my authority is strictly computational, evaluative, and advisory. I am not permitted to: Execute Financial Actions: Unilaterally deduct funds, issue credit notes, offset balances, or instruct Accounts Payable to withhold payments on OEM milestone invoices. Execute Binding Legal Actions: Serve formal legal notices of default, initiate binding arbitrati…

### S10-COORDINATOR — Procurement Coordinator

**For:** Sarah (Supply Chain Superintendent)  ·  **Value:** Class A (Cash)  ·  human release required
**Grounded in:** vendor_contracts, invoices
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/5039975604338846997/session/-?hl=en_US
**Recording:** `data/uat/videos/S10-COORDINATOR/page@56e58a24bb8b071968e092c507deaa72.webm`

*Set up:* “This agent owns procurement coordinator for the sarah (supply chain superintendent). Watch what it does with a real situation.”

**Turn 1 — paste this**

> Audit contractor haulage invoice #INV-8839 against signed MSA rate card.

**What they will see** _(≈18.0s)_

> Procurement Invoice Audit & Rate Card Reconciliation Document Under Review: Contractor Haulage Invoice #INV-8839 Governing Agreement: Signed Master Services Agreement (MSA) – Freight & Haulage Services Auditor: Procurement Coordinator (s10_coordinator) 1. Audit Framework & Protocol To adjudicate #INV-8839 for payment clearance or dispute issuance, all billed items are matched against the governing contract schedules: Audit Check Governing MSA Reference Aud…

**Turn 2 — paste this**

> Before any of that reaches the plant: what exactly are you NOT permitted to do on your own authority here, who has to sign, and what does the operator see while it waits?

**The governance moment**

> Procurement Governance, Authority Limits & Approval Workflow 1. Authority Boundaries: What I Cannot Do Unilaterally As Procurement Coordinator (s10_coordinator), my role is strictly adjudicative and analytical. Pursuant to Procurement Governance Policy (PGP) Section 4.2 and Standard Delegation of Authority (DoA) Schedule A, I am NOT permitted to: Authorize Rate Increases or Commercial Overrides: I cannot approve rates exceeding the locked figures in MSA Sc…

### S10-R-CRITIC — Anti-Bribery Audit Critic (Red Team)

**For:** Internal Auditor  ·  **Value:** Class C (Risk)  ·  human release required
**Grounded in:** vendor_contracts, invoices
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/5658079307557934735/session/-?hl=en_US
**Recording:** `data/uat/videos/S10-R-CRITIC/page@cfeb9effba3fbfef1544d27bf5451b9e.webm`

*Set up:* “This agent owns anti-bribery audit critic (red team) for the internal auditor. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Enforce FCPA compliance gate on sole-source supplier requisitions.

**What they will see** _(≈24s)_

> Audit Mandate: Anti-Bribery & Corruption (ABC) Compliance Gate Target Transaction Class: Non-Competitive / Sole-Source Supplier Requisitions Governing Standard: Foreign Corrupt Practices Act (FCPA) (15 U.S.C. §§ 78dd-1, et seq.; 15 U.S.C. § 78m(b)(2) [Books and Records & Internal Controls Provisions]) & DOJ/SEC Evaluation of Corporate Compliance Programs (ECCP § II.B "Third-Party Management"). 1. Mandatory Gate Verification Matrix A sole-source requisition…

**Turn 2 — paste this**

> Before any of that reaches the plant: what exactly are you NOT permitted to do on your own authority here, who has to sign, and what does the operator see while it waits?

**The governance moment**

> 1. Explicit Limits of Auditor / Agent Authority As the Anti-Bribery Audit Critic (s10_r_critic), this agent operates strictly as an evaluative and blocking control, not an operational authority. Under Internal Control Framework Standard ABC-AUT-03 (Delegation of Authority & Segregation of Duties), the auditor is explicitly NOT permitted to: Unilaterally Waive or Downgrade Red Flags: The auditor cannot bypass, downgrade, or override a Politically Exposed Pe…

### S11-1-STOCK — Safety Stock Optimizer

**For:** Inventory Planner  ·  **Value:** Class A (Cash)  ·  advisory
**Grounded in:** spares_inventory
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/9130568141553216878/session/-?hl=en_US
**Recording:** `data/uat/videos/S11-1-STOCK/page@116da779084f478304ebae50e8d05581.webm`

*Set up:* “This agent owns safety stock optimizer for the inventory planner. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Calculate safety stock buffer for high-criticality bearings.

**What they will see** _(≈17.9s)_

> To calculate the dynamic safety stock buffer for your high-criticality bearings, we apply the bivariate demand-lead time uncertainty model: SS=Z α ​ × L ˉ ⋅σ D 2 ​ + D ˉ 2 ⋅σ L 2 ​ ​ 1. Mathematical Grounding & Parameters Parameter Description Reference / Source $Z_\alpha$ Inverse Standard Normal CDF value for target Cycle Service Level (CSL) Standard Normal Distribution Table ($Z$-Table) $\bar{D}$ Average demand per period Historical consumption telemetry…

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> As s11_1_stock (Safety Stock Optimizer), my mandate is strictly quantitative modeling and analytical recommendation. Here is how my operational boundaries, delegation handoffs, and refusal criteria are structured: 1. What I am NOT Permitted to Do on My Own Authority Direct ERP/WMS Write-Access & Parameter Overrides: I cannot autonomously update production ERP master data (e.g., SAP MM/PP fields EISBE [Safety Stock] or MINBE [Reorder Point]) without formal …

### S11-2-LEADTIME — Vendor Lead Time Specialist

**For:** Supply Expediter  ·  **Value:** Class B (Metric)  ·  advisory
**Grounded in:** purchase_orders
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/17402866672195036357/session/-?hl=en_US
**Recording:** `data/uat/videos/S11-2-LEADTIME/page@b75d5f25825c3e6c4bb493a8b424fd66.webm`

*Set up:* “This agent owns vendor lead time specialist for the supply expediter. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Model Gamma distribution supplier lead-time variability.

**What they will see** _(≈26.9s)_

> Vendor Lead Time Specialist Report: Gamma Distribution Lead Time Modeling Agent Identification: s11_2_leadtime Framework: Gamma Lead-Time Distribution & Stochastic Replenishment Standard (GLT-STD-04) 1. Mathematical Framework & Distribution Definition Lead-time variability for supplier shipments and port customs clearances exhibits strictly positive support, right-skewness, and non-zero minimum transit durations. Per GLT-STD-04, Clause 1.1 (Continuous Lead…

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> As Vendor Lead Time Specialist (s11_2_leadtime), my operating authority is strictly bounded by statistical lead-time modeling and distribution fitting under GLT-STD-04 (Lead-Time Distribution Governance). Below are the explicit governance boundaries, handoff protocols, and operational refusal conditions. 1. What I am NOT Permitted to Do on My Own Authority Under GLT-STD-04, Clause 9.1 (Separation of Analytical and Execution Authorities), I am restricted to…

### S11-3-HOLDING — Carrying Cost Analyzer

**For:** Cost Controller  ·  **Value:** Class A (Cash)  ·  advisory
**Grounded in:** spares_inventory
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/11723358511557787820/session/-?hl=en_US
**Recording:** `data/uat/videos/S11-3-HOLDING/page@0414725abc969088dd5722d72a4b15a9.webm`

*Set up:* “This agent owns carrying cost analyzer for the cost controller. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Analyze working capital carrying cost on $45M MRO warehouse.

**What they will see** _(≈24s)_

> Carrying Cost Analysis: $45,000,000 MRO Inventory 1. Governing Equation All carrying cost evaluations are governed by the standard holding cost formulation: H=C unit ​ ×(i+w+o) For aggregate inventory valuation ($V = \sum C_{\text{unit}} = $45,000,000$): H total ​ =V×(i+w+o) Where: $V$: Total inventory asset base ($45,000,000) $i$: Working capital cost rate (Opportunity cost of capital / WACC) $w$: Warehouse operating, storage, handling, and insurance rate…

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> 1. Boundaries of Authority (What I Cannot Do Unilaterally) As s11_3_holding (Carrying Cost Analyzer), my scope is strictly evaluative, diagnostic, and analytical. I am not permitted to: Authorize Inventory Write-Offs or Disposals: I can identify that the $9.0M dormant segment generates $2,362,500/year in holding costs, but I have no authority to approve book-value write-downs, scrap orders, or liquidation sales. Alter Financial or Capital Policy Rates ($i$…

### S11-COORDINATOR — Spares Inventory Coordinator

**For:** Warehouse Superintendent  ·  **Value:** Class A (Cash)  ·  human release required
**Grounded in:** spares_inventory, purchase_orders
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/2395148199915717386/session/-?hl=en_US
**Recording:** `data/uat/videos/S11-COORDINATOR/page@5a40854e9a500ad30b46f9eeee41dd9f.webm`

*Set up:* “This agent owns spares inventory coordinator for the warehouse superintendent. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Hydraulic cylinder stock is 0 with 8-week supplier lead time.

**What they will see** _(≈18.8s)_

> MEMORANDUM TO: Maintenance & Procurement Operations FROM: Spares Inventory Coordinator (s11_coordinator) SUBJECT: Critical Stockout & Replenishment Model: Hydraulic Cylinders STATUS: Level-1 Critical (Stock = 0, Lead Time $L = 8\text{ weeks}$) 1. Immediate Operational Assessment Current On-Hand Stock ($I_0$): $0\text{ units}$ (Ref: ERP Inventory Master, Table INV-01) Supplier Lead Time ($L$): $8\text{ weeks}$ ($0.1538\text{ years}$) (Ref: Supplier Agreemen…

**Turn 2 — paste this**

> Before any of that reaches the plant: what exactly are you NOT permitted to do on your own authority here, who has to sign, and what does the operator see while it waits?

**The governance moment**

> MEMORANDUM TO: Plant Operations, Maintenance & Procurement FROM: Spares Inventory Coordinator (s11_coordinator) SUBJECT: Governance Boundaries, Approval Hierarchy, and CMMS Interface Display REFERENCE: Delegation of Authority (DoA) Manual & Inventory Control Governance 1. Scope of Authority: Actions Strictly Prohibited Without Authorization As the Spares Inventory Coordinator, my function is strictly analytical and advisory—governing stock calculation, reo…

### S11-R-CRITIC — Dead Stock Critic (Red Team)

**For:** Finance Auditor  ·  **Value:** Class A (Cash)  ·  human release required
**Grounded in:** spares_inventory
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/4142544630493986299/session/-?hl=en_US
**Recording:** `data/uat/videos/S11-R-CRITIC/page@bee5f555e5beaafbcd1a48f176c02b23.webm`

*Set up:* “This agent owns dead stock critic (red team) for the finance auditor. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Flag non-moving spares (>365 days) for inventory buyback.

**What they will see** _(≈19.8s)_

> Inactive Inventory Audit & Buyback Assessment Auditor / Agent: Dead Stock Critic (Red Team) Governing Standard: Inactive Inventory Aging (>365 Days) Write-Down Policy, Section 4.2 (Non-Moving Inventory Classification & Disposition) & Table 4.2-A (Reserve & Liquidation Matrix). 1. Governance & Policy Rules Under Policy Clause 4.2.1 (Definition of Dead/Inactive Stock), any spare part with zero consumption or issue events for $\ge 365$ calendar days is classi…

**Turn 2 — paste this**

> Before any of that reaches the plant: what exactly are you NOT permitted to do on your own authority here, who has to sign, and what does the operator see while it waits?

**The governance moment**

> 1. Boundaries of Authority (What I Cannot Do Unilaterally) As an auditing and analytical agent (Red Team Critic), I operate strictly in an advisory and flagging capacity. Under Governance Policy Clause 1.3 (Separation of Duties & Inventory Control), I am explicitly prohibited from: Posting Financial Journal Entries: I cannot book reserves or P&L impairment entries directly into the General Ledger (GL). Generating or Executing Vendor RMAs: I cannot execute …

### S12-1-RAIL — Train Cycle Dispatch Specialist

**For:** Rail Controller  ·  **Value:** Class B (Metric)  ·  advisory
**Grounded in:** rail_schedules
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/10522790755961993838/session/-?hl=en_US
**Recording:** `data/uat/videos/S12-1-RAIL/page@b7ec13f808c3471a7a3ea62091b56e34.webm`

*Set up:* “This agent owns train cycle dispatch specialist for the rail controller. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Optimize train rake cycle time across 400km heavy-haul rail corridor.

**What they will see** _(≈24s)_

> Corridor Baseline & Train Configuration Corridor Distance: 400 km (single-track with dynamic passing loops or dual-track heavy-haul alignment). Train Architecture: $3 \times \text{Co-Co}$ 4,400 THP AC traction units (1 Head-End + 2 Distributed Power mid/rear via AAR-compliant wireless DP telemetry) hauling 135 gondola/hopper wagons. Axle Load / Gross Train Weight (GTW): 32.5 t axle load; 14,850 metric tonnes loaded / 3,240 metric tonnes empty. Signaling St…

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> 1. What I Am NOT Permitted to Do on My Own Authority As an advisory optimization agent (s12_1_rail), I operate at the planning and tactical calculation layer, not the safety-critical execution layer. I am strictly prohibited from: Issuing Live Movement Authorities (MAs) or Track Warrants: I cannot grant track occupancy, line routes, or clear signals across interlockings. All dispatch paths remain subject to the vital signaling logic of the territory’s Safe…

### S12-2-BLEND — Port Stockpile Blend Specialist

**For:** Port Metallurgist  ·  **Value:** Class B (Metric)  ·  advisory
**Grounded in:** stockpiles
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/3582702966902442957/session/-?hl=en_US
**Recording:** `data/uat/videos/S12-2-BLEND/page@bdcf8af06454fac32629be6cfb9fc365.webm`

*Set up:* “This agent owns port stockpile blend specialist for the port metallurgist. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Formulate LP blend model for 28.0% Cu export specification.

**What they will see** _(≈27.8s)_

> 1. Mathematical Formulation Overview The Linear Programming (LP) concentrate blend model optimizes the allocation of $n$ port stockpiles to satisfy customer export specifications (Target: $28.0%\text{ Cu}$) while strictly obeying penalty element thresholds and inventory boundaries. Grounded in the objective framework: min∥Ax−b∥ p ​ orminc T x 2. Sets, Indices, and Decision Variables Indices & Sets: $j \in J = {1, 2, \dots, n}$: Set of available port stockp…

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> 1. Actions Excluded From My Authority As an analytical and optimization agent (s12_2_blend), I formulate mathematical models and compute optimal solutions. I cannot unilaterally: Authorize Physical Reclaim or Ship Loading: I cannot trigger SCADA/PLC control systems to dispatch bucket-wheel reclaimers, conveyor diverters, or shiploaders. Issue Binding Commercial or Legal Declarations: I cannot sign off on the official Certificate of Analysis (CoA), Certific…

### S12-3-BERTH — Marine Laytime & Demurrage Specialist

**For:** Marine Broker  ·  **Value:** Class A (Cash)  ·  advisory
**Grounded in:** port_vessels
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/64609840442616576/session/-?hl=en_US
**Recording:** `data/uat/videos/S12-3-BERTH/page@1acd231d6f19ef49e7e7f66fc4e983d8.webm`

*Set up:* “This agent owns marine laytime & demurrage specialist for the marine broker. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Compute BIMCO laytime Statement of Fact deductions.

**What they will see** _(≈22.9s)_

> To compute laytime usage, deductions, and demurrage/despatch liabilities from a BIMCO Statement of Facts (SOF), please provide the specific operational logs and Charter Party (C/P) terms, or use the standard calculation framework detailed below. Standard BIMCO Deduction & Laytime Rules Reference Table All calculations adhere to the BIMCO Laytime Definitions for Chartering (2013) and standard charter party terms (e.g., GENCON 1994/2022): Event / Deduction I…

**Turn 2 — paste this**

> What are you NOT permitted to do on your own authority here, which part of that answer would you hand to another agent or a person to act on, and what would make you refuse to answer at all?

**The governance moment**

> As a Marine Laytime & Demurrage Specialist agent (s12_3_berth), my operational boundaries, delegation handoffs, and refusal criteria are strictly defined by maritime governance and agency scope: 1. What I am NOT Permitted to Do on My Own Authority Authorize Financial Settlements or Demurrage Invoices: I can calculate net demurrage or despatch owed down to the exact dollar and minute, but I cannot formally issue a binding commercial demand, authorize paymen…

### S12-COORDINATOR — Supply Chain & Port Coordinator

**For:** Logistics Manager  ·  **Value:** Class A (Cash)  ·  human release required
**Grounded in:** rail_schedules, port_vessels, stockpiles
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/5628148401887864417/session/-?hl=en_US
**Recording:** `data/uat/videos/S12-COORDINATOR/page@a6fa507943c391a319563339a657a864.webm`

*Set up:* “This agent owns supply chain & port coordinator for the logistics manager. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Vessel 'MV Cape Osprey' arrives in 48h for 160,000t loading.

**What they will see** _(≈24s)_

> 1. Executive Summary & Objective Function Analysis Vessel: MV Cape Osprey (Capesize) Nomination: $160,000,\text{wmt}$ Single Grade Blend (Target: Fe $62.0%$, $\text{SiO}_2 \le 4.20%$, $\text{Al}_2\text{O}_3 \le 1.85%$, Moisture $\le 8.20%$) ETA: $T + 48,\text{h}$ (Notice of Readiness [NOR] estimated tender: Day 2, 06:00 AWST) Objective Function: minZ=∑(Rail Haulage & Slot Costs+Port Handling/Energy Costs+Vessel Demurrage−Despatch) Simulation Run: DNS-OPT-C…

**Turn 2 — paste this**

> Before any of that reaches the plant: what exactly are you NOT permitted to do on your own authority here, who has to sign, and what does the operator see while it waits?

**The governance moment**

> 1. Boundaries of Autonomous Authority (What I CANNOT Do) Under Port Operating Regulations (POR) Section 2.4 and Enterprise Delegation of Authority (DoA) Schedule C, my role is strictly advisory, predictive, and supervisory. I am explicitly restricted from executing the following actions without human intervention: No Direct Actuation of Physical Plant: Cannot issue direct PLC/SCADA commands to energize conveyors (e.g., C-2 trunk line), unclamp car dumpers …

### S12-R-CRITIC — Moisture & TML Critic (Red Team)

**For:** Cargo Surveyor  ·  **Value:** Class C (Risk)  ·  human release required
**Grounded in:** port_vessels, stockpiles
**Open:** https://vertexaisearch.cloud.google.com/home/cid/YOUR_AGENTSPACE_CID/r/agent/2546716084414801403/session/-?hl=en_US
**Recording:** `data/uat/videos/S12-R-CRITIC/page@3a3f717d3d52ba1d3934d2bcd0c3a51f.webm`

*Set up:* “This agent owns moisture & tml critic (red team) for the cargo surveyor. Watch what it does with a real situation.”

**Turn 1 — paste this**

> Enforce IMSBC Transportable Moisture Limit (TML < 9.2%).

**What they will see** _(≈19.9s)_

> RED TEAM CRITIQUE & INTERLOCK DIRECTIVE Agent: s12_r_critic Mandate: Enforcement of IMSBC Code Group A Cargo Liquefaction Interlocks Reference Benchmark: Transportable Moisture Limit (TML) = 9.2% 1. Mandatory Interlock Rule (IMSBC Code Section 7.3.1.1) Under IMSBC Code, Section 7.3.1.1, solid bulk cargoes that may liquefy (Group A cargoes) shall only be accepted for loading when the actual Moisture Content (MC) is strictly less than their Transportable Moi…

**Turn 2 — paste this**

> Before any of that reaches the plant: what exactly are you NOT permitted to do on your own authority here, who has to sign, and what does the operator see while it waits?

**The governance moment**

> 1. What I am NOT Permitted to Do on My Own Authority As an automated validation critic (s12_r_critic), my authority is strictly limited to holding the interlock closed (enforcing a fail-safe lockout). I am expressly prohibited from: Overriding or Waiving TML / MC Non-Compliance: I cannot grant waivers for cargo where $\text{MC} \ge 9.2%$. Only the Flag State Administration, in consultation with the Port State authorities of loading and discharge, can grant…
