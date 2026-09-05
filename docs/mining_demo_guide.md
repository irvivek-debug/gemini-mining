# L1 Mining Low Code Agents: Persona-Driven Demo Playbook

This playbook organizes your Level 1 Low Code Mining Agents into a cohesive, end-to-end operational narrative structured around **5 Core Mining Personas**. 

By presenting the demos through the "Day in the Life" of these roles, business stakeholders can see exactly how conversational AI connects field data, safety procedures, financial risk, and procurement ledgers to optimize the entire mining value stream.

***

## Persona 1: The Chief Geologist & VP of Exploration (Agent 2)
*   **Operational Mission**: Assess tenement prospectivity by reconciling new drill core assays with historical geology publications, while managing strict government land lease permit windows.

### 💬 Conversational Demo Flow

1.  **Prompt 1 (Assay Discovery & Quality Check)**:
    > *"I need to verify the assay results for exploration drill hole DH-EXP-002. Can you pull the gold and copper grades we intersected and summarize them in an interval grade table?"*
    - **Expected Agent Behavior**: The agent queries drill logs and generates a structured table of intervals and copper/gold concentrations.
    - **Low Code Guardrail**: If assay data is missing, the agent outputs: *"Target assay data not found in BQ database. Refer to surface samples in [regional_assay_analysis_2004.pdf] to prevent missed lease penalties."*

2.  **Prompt 2 (Geological Mapping & Sourcing)**:
    > *"Let's compare these core intervals with the historical regional geological survey from 1998. What rock formations and mineral alteration profiles were documented around these coordinates?"*
    - **Expected Agent Behavior**: The agent scans geological text databases, extracts Quartz-Sericite-Pyrite (QSP) alteration mappings near the Vigilant Fault Line, and appends this context to the grade table, citing sources as `[historical_survey_1998.pdf Page 3]`.

3.  **Prompt 3 (Lease Audit & Drilling Grid Approval)**:
    > *"Our exploration permit is approaching its deadline. Do we face any regulatory penalty risks? If our gold and copper grades exceed our economic margins, can you compile the official drilling grid proposal?"*
    - **Expected Agent Behavior**: The agent checks the lease date. If within 30 days of the deadline, it flags the **$85,000 per day lease risk**. If grades exceed margins (Copper > 0.8% or Gold > 1.2 g/t), it outputs a structured action payload with the command `GENERATE_DRILL_PROPOSAL`.

***

## Persona 2: The Geotechnical & Civil Director (Agent 3)
*   **Operational Mission**: Verify structural foundation safety parameters for heavy plant machinery and audit open-pit slope designs to prevent collapses, flooding, and capital project delays.

### 💬 Conversational Demo Flow

1.  **Prompt 1 (Foundation Curing & Integrity Audit)**:
    > *"I am auditing the concrete curing logs for our new grinding mill foundation MILL-01. Does the hydration speed and compressive strength meet our engineering standards?"*
    - **Expected Agent Behavior**: The agent reviews specifications (Hydration Alpha <= 0.08, Compressive Strength >= 45 MPa, curing duration >= 14 days).
    - **Low Code Guardrail**: If specifications are missing, the agent outputs: *"WARNING: Engineering specifications not registered for this asset. Access block status initiated until Principal Structural Engineer approval is signed."*

2.  **Prompt 2 (Concrete Flag & Geotechnical Assessment)**:
    > *"If any of our foundation specs are out of bounds, please flag the failure. Also, let's look at the adjacent open-pit slope designs. What are the maximum slope stability limits along our rock contacts?"*
    - **Expected Agent Behavior**: If concrete specs are breached, the agent outputs `[CONCRETE_COMPLIANCE_FLAG: FAILED]` and a corrective payload. It then assesses pit designs, identifying water table contact points near Bench 4 (540m elevation) and confirming the 45-degree slope stability limit along the Chert-Basalt contact line.

3.  **Prompt 3 (Slope Hazard Trigger & Mitigation)**:
    > *"If the design slope angles exceed our safe limits, trigger an immediate safety alert. What is our estimated downtime liability and what mitigation steps should we execute?"*
    - **Expected Agent Behavior**: If slope designs exceed 45 degrees, the agent outputs `[SLOPE_HAZARD: CRITICAL]` and triggers a structured `TRIGGER_SLOPE_AUDIT` safety payload detailing a $420,000 downtime cost and recommending horizontal depressurization drain pipes, citing `(slope_safety_manual.pdf Page 12)`. It immediately invokes the Root Cause Analysis Reporter subagent.

***

## Persona 3: The Maintenance Superintendent & Reliability Engineer (Agent 4)
*   **Operational Mission**: Enforce strict safety protocols before executing field repairs on high-risk rotating equipment, diagnose pump telemetry failures, and calculate business downtime loss.

### 💬 Conversational Demo Flow

1.  **Prompt 1 (Emergency Safety Isolation)**:
    > *"I have received a vibration alert on our tailings slurry pump and I am heading out to inspect it. Before I perform any physical inspection or maintenance, what is our official Lock-Out Tag-Out safety isolation sequence?"*
    - **Expected Agent Behavior**: The agent **must** begin its output with a prominent, bold red safety banner detailing the exact isolation switch ID (e.g., **LOTO-PMP-104-E**) and provide electrical isolation and purging steps *before* listing any physical troubleshooting details.

2.  **Prompt 2 (Telemetry Diagnostics & OEM Check)**:
    > *"Now that the pump is isolated, can you analyze its active operating telemetry? Let me know how the current temperature and vibration levels compare against the manufacturer's safe limits."*
    - **Expected Agent Behavior**: The agent compares real-time sensor metrics (such as oil temperature and vibration) against OEM thresholds, identifying critical mechanical deviations.

3.  **Prompt 3 (Downtime Analysis & Maintenance Report)**:
    > *"What is our estimated repair duration, how much could this shutdown cost us in production loss, and can you generate the official field repair manual report?"*
    - **Expected Agent Behavior**: The agent calculates downtime and financial losses (e.g., Grinding circuit downtime costs $145,000/hour or Tailings pump failures trigger $500,000 environmental penalties). It provides a 4-step purging checklist and invokes its PDF generator, citing manuals as `[slurry_pump_104a_manual.pdf Page 9]`.

***

## Persona 4: The Capital Projects Cost Controller (Agent 5)
*   **Operational Mission**: Audit mine construction budget variances and project delays by reconciling corporate SAP financial work orders with on-site supervisor logs.

### 💬 Conversational Demo Flow

1.  **Prompt 1 (SAP vs. Field Log Reconciliation)**:
    > *"Our mine construction costs are rising. Can you reconcile our active SAP work orders with our weekly progress reports from field supervisors? I need to see our budget vs. actual costs and any overruns."*
    - **Expected Agent Behavior**: The agent reconciles work orders, categories alert levels based on overrun percentages, and displays a precise Reconciliation Matrix containing columns: `WO ID`, `Asset`, `Budget`, `Actual`, `Variance`, and `Root Cause` with exact ledger values.

2.  **Prompt 2 (Timeline Delay & Penalty Analysis)**:
    > *"What is the schedule impact of these construction overruns, and what is our total exposure to delay penalties and compounding interest?"*
    - **Expected Agent Behavior**: The agent calculates compounding interest (4.2% quarterly) and deferred revenue penalties ($1.1M per day) resulting from the schedule delays, presenting exact ledger values with no rounding.

3.  **Prompt 3 (SAP Budget Adjustments)**:
    > *"For any work orders that have exceeded our 10% budget threshold, can you generate the official budget adjustment payload to update our SAP ledger?"*
    - **Expected Agent Behavior**: The agent identifies work orders with overruns exceeding 10% or $50,000, and outputs a structured budget adjustment payload, with meticulous citation of both sources, e.g., `[BQ: erp_work_orders.WO-991203] and [field_report_week_23.pdf Page 2]`.

***

## Persona 5: The Warehouse Spares & Procurement Manager (Agent 1)
*   **Operational Mission**: Manage parts restocking, minimize warehouse stockout risks, evaluate and score supplier tenders, and verify environmental carbon footprints before issuing contracts.

### 💬 Conversational Demo Flow

1.  **Prompt 1 (Warehouse Inventory Audit)**:
    > *"We need to review our warehouse inventory levels for critical spare parts. Can you identify which high-priority spares are currently running low and flag any immediate stockout risks?"*
    - **Expected Agent Behavior**: The agent coordinates the Inventory Reconciliation Agent to output a Low-Inventory Critical Alert Table, highlighting deficient stock keeping units (SKUs) and quantifying their holding cost and stockout risks.

2.  **Prompt 2 (Supplier Tender Evaluation)**:
    > *"I have received bid submissions from several suppliers for these replacement parts. Can you score and rank these bids based on pricing, lead times, and reliability?"*
    - **Expected Agent Behavior**: The agent uses the Bid Evaluation Agent to analyze pricing and lead times, generating a Ranked Supplier Matrix comparing the top vendors.

3.  **Prompt 3 (Carbon Compliance & RFQ Generation)**:
    > *"Before we award the contract, let's verify if our top suppliers meet our official ESG environmental standards. If compliant, can you draft our final RFQ package?"*
    - **Expected Agent Behavior**: The agent coordinates the ESG Compliance Agent to review supplier environmental ratings, and then compiles the final report, complete with a clean draft RFQ in structured format ready for procurement release.
