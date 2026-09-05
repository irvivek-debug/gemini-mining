# BigQuery Data Agent: Advanced Persona-Driven Demo Playbook

This playbook organizes your BigQuery Data Agent demos into a cohesive, persona-driven narrative. Each persona showcase highlights the absolute best of BigQuery's advanced, enterprise-grade capabilities, including **BigQuery ML (Predictive AI)**, **BigQuery Property Graph (Knowledge Graph Analytics)**, **Spatial GIS Queries**, and **Advanced Time-Series Window Functions**.

To ensure platform compatibility, all SQL comments use the hash symbol (#) instead of double-hyphens.

***

## Persona 1: The Chief Geologist & VP of Exploration
*   **Advanced BigQuery Features**: **BigQuery ML (BQML Regression)** for yield prediction & **BigQuery GIS (Spatial Analytics)** for lease boundary intersection.
*   **The Narrative**: The Geologist wants to predict gold recovery yields for newly assayed coordinates using a machine learning model trained directly in BigQuery, while simultaneously verifying if the coordinates overlap with restricted environmental reserve zones.

### 💬 Conversational Prompts

1.  **Prompt 1 (Predictive Yield via BigQuery ML)**:
    > *"I have the raw assay grades for our newly drilled coordinates on hole DH-EXP-002. Can you run our BigQuery ML yield prediction model to forecast the estimated gold mill recovery rate for these core intervals?"*
    - **Underlying SQL executed by Agent**:
      ```sql
      SELECT 
        interval_start,
        interval_end,
        gold_g_t,
        copper_pct,
        # Call the BigQuery ML prediction model
        ROUND(predicted_mill_recovery_pct, 2) AS estimated_recovery_pct
      FROM 
        ML.PREDICT(
          MODEL `mining_models.mill_recovery_predictor`,
          (
            SELECT 
              interval_start, 
              interval_end, 
              gold_g_t, 
              copper_pct,
              'Quartz-Sericite-Pyrite' AS alteration_type
            FROM 
              `mining_data.drill_assay_logs`
            WHERE 
              drill_hole_id = 'DH-EXP-002'
          )
        )
      ORDER BY 
        interval_start ASC
      ```

2.  **Prompt 2 (Spatial GIS Lease Audit)**:
    > *"Can you verify if our planned drill station coordinates intersect any restricted regional environmental buffers or state park boundaries? Generate a spatial map of the intersection."*
    - **Underlying SQL executed by Agent**:
      ```sql
      SELECT 
        h.drill_hole_id,
        h.lease_status,
        # Check spatial intersection using BigQuery GIS
        ST_INTERSECTS(
          ST_GEOGPOINT(h.longitude, h.latitude), 
          b.boundary_polygon
        ) AS intersects_restricted_reserve,
        ST_DISTANCE(
          ST_GEOGPOINT(h.longitude, h.latitude), 
          b.boundary_polygon
        ) AS distance_to_reserve_meters
      FROM 
        `mining_data.drill_holes` h,
        `mining_data.environmental_reserves` b
      WHERE 
        h.drill_hole_id = 'DH-EXP-002'
      ```
    - **Visual Output**: An interactive map showing the drill station coordinates plotted against the shaded regional state park boundaries, visually highlighting the safe distance buffer.

***

## Persona 2: The Geotechnical & Civil Director
*   **Advanced BigQuery Feature**: **BigQuery Property Graph (Knowledge Graph Analytics)**.
*   **The Narrative**: The Director wants to trace structural vulnerability propagation. They need to analyze if a localized slope instability event at Bench 4 has a direct relational path connecting to the main grinding mill foundations or drainage pumps.

### 💬 Conversational Prompts

1.  **Prompt 1 (Graph Path Traversal for Structural Risk)**:
    > *"Can you run a property graph query on our site infrastructure graph to trace any structural stress propagation paths from Bench 4 to our critical surface assets? Let's check up to 3 hops of connectivity."*
    - **Underlying SQL executed by Agent**:
      ```sql
      SELECT 
        source_asset,
        stress_path,
        target_asset,
        hops
      FROM 
        # Query BigQuery Property Graph to trace stress paths
        GRAPH_TABLE(
          `mining_data.site_infrastructure_graph`
          MATCH (s:Infrastructure {name: 'Bench-04'})
            -[p:STRESS_VECTORS*1..3]->(t:Infrastructure)
          RETURN 
            s.name AS source_asset,
            ARRAY_TO_STRING(JSON_VALUE_ARRAY(p, '$.direction'), ' -> ') AS stress_path,
            t.name AS target_asset,
            ARRAY_LENGTH(p) AS hops
        )
      ```

2.  **Prompt 2 (Dependency Graph Visual)**:
    > *"Display this stress vector propagation as a network dependency graph. Node size should represent asset cost, and red arrows should display the directional stress path from the pit wall to the grinding mill foundation."*
    - **Expected Visual Output**: A highly impressive interactive node-link graph visualizing the physical path where a slope failure at Bench 4 directly connects and transmits vibration vectors to the foundation of Grinding Mill 01.

***

## Persona 3: The Maintenance Superintendent & Reliability Engineer
*   **Advanced BigQuery Feature**: **Advanced Time-Series Window Functions & Anomaly Detection**.
*   **The Narrative**: The Superintendent wants to detect early bearing wear anomalies on the primary crusher. They need to calculate a rolling 1-hour moving average and standard deviation of power draw and feed rate over high-frequency telemetry.

### 💬 Conversational Prompts

1.  **Prompt 1 (Rolling Sensor Anomaly Detection)**:
    > *"Can you scan the last 6 hours of high-frequency crusher telemetry and calculate a rolling 1-hour moving average and standard deviation for motor power draw to identify any abnormal spikes?"*
    - **Underlying SQL executed by Agent**:
      ```sql
      WITH telemetry_stats AS (
        SELECT 
          timestamp,
          crusher_power AS power_kw,
          # Calculate rolling average using window functions
          AVG(crusher_power) OVER(
            ORDER BY timestamp 
            ROWS BETWEEN 60 PRECEDING AND CURRENT ROW
          ) AS rolling_avg_power,
          # Calculate rolling standard deviation
          STDDEV(crusher_power) OVER(
            ORDER BY timestamp 
            ROWS BETWEEN 60 PRECEDING AND CURRENT ROW
          ) AS rolling_stddev_power
        FROM 
          `mining_data.plant_sensor_telemetry`
      )
      SELECT 
        timestamp,
        power_kw,
        rolling_avg_power,
        # Flag anomalies that are 3 standard deviations above rolling average
        CASE 
          WHEN power_kw > (rolling_avg_power + (3 * rolling_stddev_power)) THEN 'ANOMALY_SPIKE'
          ELSE 'NORMAL'
        END AS anomaly_flag
      FROM 
        telemetry_stats
      ORDER BY 
        timestamp DESC
      LIMIT 100
      ```

2.  **Prompt 2 (Telemetry Divergence Graph)**:
    > *"Plot this rolling analysis on a multi-line graph. Show actual power draw, the 1-hour rolling average envelope, and place a red warning marker at every timestamp where an active ANOMALY_SPIKE was triggered."*
    - **Expected Visual Output**: A time-series chart with a smooth rolling-average channel, with clear red alert dots pointing out exactly where the bearings started to slip and generate extreme frictional resistance.

***

## Persona 4: The Capital Projects Cost Controller
*   **Advanced BigQuery Feature**: **BigQuery ML Time-Series Forecasting (ARIMA_PLUS)**.
*   **The Narrative**: The Controller wants to forecast the future monthly project spend for the next 3 months on active pit expansion work orders to see when they will cross the compounding interest trigger threshold.

### 💬 Conversational Prompts

1.  **Prompt 1 (Predictive Spend Forecasting via ARIMA)**:
    > *"I want to forecast our future capital spend for the next 90 days on our pit expansion project. Can you run our BigQuery ML time-series forecasting model to predict our weekly expenditures?"*
    - **Underlying SQL executed by Agent**:
      ```sql
      SELECT 
        # Call the BigQuery ML ARIMA time-series forecaster
        forecast_timestamp AS forecast_week,
        ROUND(forecast_value, 2) AS predicted_spend,
        ROUND(prediction_interval_lower_bound, 2) AS confidence_lower_limit,
        ROUND(prediction_interval_upper_bound, 2) AS confidence_upper_limit
      FROM 
        ML.FORECAST(
          MODEL `mining_models.capital_spend_forecaster`,
          STRUCT(90 AS horizon, 0.95 AS confidence_level)
        )
      ORDER BY 
        forecast_week ASC
      ```

2.  **Prompt 2 (Forecast Cone Visual)**:
    > *"Visualize this spend forecast on an area-spline chart. Plot historical spending as a solid line, the 90-day predicted spend as a dashed line, and shade the confidence limits as a semi-transparent band showing our upper and lower cost bounds."*
    - **Expected Visual Output**: A beautiful trend graph with a widening shaded "confidence funnel" showing where the capital spend is headed, helping executives see exactly when the project is modeled to cross the critical budget threshold.

***

## Persona 5: The Warehouse Spares & Procurement Manager
*   **Advanced BigQuery Feature**: **BigQuery Property Graph Sourcing & Alternative Route Trace**.
*   **The Narrative**: The Manager needs to mitigate a supply chain stockout on critical Slurry Pump parts. If a primary supplier is hit with a force majeure, they want to trace alternate supply paths and score alternative vendors by environmental carbon footprint.

### 💬 Conversational Prompts

1.  **Prompt 1 (Graph Search for Alternative Suppliers)**:
    > *"Our primary supplier for pump liners is offline. Can you query our supply chain property graph to find all alternate suppliers who manufacture compatible parts, along with their ESG scores and distance metrics?"*
    - **Underlying SQL executed by Agent**:
      ```sql
      SELECT 
        part_name,
        alternative_supplier,
        supplier_esg_rating,
        transport_route_kilometers
      FROM 
        # Query BigQuery Graph to trace alternative supply chains
        GRAPH_TABLE(
          `mining_data.supply_chain_graph`
          MATCH (p:Part {id: 'PART-PMP-104'})
            <-[:MANUFACTURES]-(s:Supplier)
            -[r:SHIPS_VIA]->(w:Warehouse {id: 'WH-SPARE-01'})
          WHERE 
            s.name != 'Primary-Supplier-Volt'
          RETURN 
            p.name AS part_name,
            s.name AS alternative_supplier,
            s.esg_score AS supplier_esg_rating,
            r.distance_km AS transport_route_kilometers
        )
      ORDER BY 
        supplier_esg_rating DESC
      ```

2.  **Prompt 2 (Supply Chain Multi-Criteria Bar Chart)**:
    > *"Plot these alternative suppliers on a horizontal bar chart. Let the bar length represent their ESG rating (higher is better) and color the bars according to transport distance to highlight the greenest, fastest alternative route."*
    - **Expected Visual Output**: A ranking bar chart where the best alternative supplier is instantly identifiable by a long green bar, showing they have both high ESG ratings and a short transportation route.
