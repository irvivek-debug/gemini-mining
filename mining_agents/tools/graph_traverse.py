"""The four canonical property-graph traversals, parameter-bound.

Edge LABELS, never table names. A graph over unmatched tables returns zero
rows with no error, so the tests pin real row counts on known-good keys.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from mining_agents.config import settings
from mining_agents.tools.base import ToolFailure, tool
from mining_agents.tools.bq_query import run_query


@dataclass(frozen=True)
class Traversal:
    graph: str
    sql: str
    params: tuple[str, ...]
    tables_read: tuple[str, ...] = field(default_factory=tuple)


def _sql(template: str) -> str:
    """Substitute the configured dataset name into a SQL template."""
    ds = settings().dataset
    return template.replace("{ds}", ds)


_BLAST_RADIUS_TMPL = """
SELECT * FROM GRAPH_TABLE(
  {ds}.MiningAssetGraph
  MATCH (origin:assets WHERE origin.asset_id = @asset_id)
        -[:DEPENDS_ON]->{1,3} (impacted:assets)
  COLUMNS (origin.asset_id AS fail_origin,
           impacted.asset_id AS impacted_asset,
           impacted.criticality_rating AS impacted_criticality)
)
"""

_STOCKOUT_EXPOSURE_TMPL = """
SELECT * FROM GRAPH_TABLE(
  {ds}.MiningSupplyChainGraph
  MATCH (p:SparePart WHERE p.part_number IN UNNEST(@below_rop_parts))
        <-[:REPLACED_PART]- (wo:WorkOrder) <-[:HAS_WORK_ORDER]- (a:Asset)
  COLUMNS (p.part_number AS part_number, wo.work_order_id AS work_order_id,
           wo.priority AS priority, wo.repair_cost AS repair_cost,
           a.asset_id AS asset_id, a.criticality_rating AS criticality_rating)
)
WHERE @asset_id IS NULL OR asset_id = @asset_id
ORDER BY part_number, work_order_id
"""

_FATIGUE_TO_INCIDENT_TMPL = """
SELECT * FROM GRAPH_TABLE(
  {ds}.MiningOperationsSafetyGraph
  MATCH (f:FatigueLog) -[:LOGGED_FOR]->
        (o:Operator WHERE o.operator_id = @operator_id)
        -[:OPERATES]-> (v:Vehicle) -[:INVOLVED_IN]-> (i:Incident)
  COLUMNS (f.log_id AS log_id, o.operator_id AS operator_id,
           v.vehicle_id AS vehicle_id, i.incident_id AS incident_id,
           i.severity_level AS severity_level)
)
"""

_ONTOLOGY_RELATED_TMPL = """
SELECT * FROM GRAPH_TABLE(
  {ds}.MiningOntologyGraph
  MATCH (s:ontology_concepts WHERE s.concept_name = @concept)
        -[r:RELATED_TO]-> (o:ontology_concepts)
  COLUMNS (s.concept_name AS subject, r.predicate AS predicate,
           o.concept_name AS object)
)
"""


def _tables(*names: str) -> tuple[str, ...]:
    ds = settings().dataset
    return tuple(f"{ds}.{name}" for name in names)


TRAVERSALS: dict[str, Traversal] = {
    "blast_radius": Traversal(
        graph="MiningAssetGraph",
        sql=_sql(_BLAST_RADIUS_TMPL),
        params=("asset_id",),
        tables_read=_tables("assets", "asset_dependencies"),
    ),
    "stockout_exposure": Traversal(
        graph="MiningSupplyChainGraph",
        sql=_sql(_STOCKOUT_EXPOSURE_TMPL),
        params=("below_rop_parts", "asset_id"),
        # procurement_bids and bid_parts_edge appear in no part of this MATCH
        # pattern. They are declared because BigQuery resolves a GRAPH_TABLE
        # query to every table backing the graph, not to the subset the pattern
        # walks — confirmed by dry run against MiningSupplyChainGraph. The other
        # three traversals happen to walk their whole graph, so this is the only
        # one where the gap is visible. Declaring the pattern's tables alone made
        # meta.tables_read understate what the query actually reaches.
        tables_read=_tables(
            "inventory_levels", "erp_work_orders",
            "work_order_parts_edge", "assets",
            "procurement_bids", "bid_parts_edge",
        ),
    ),
    "fatigue_to_incident": Traversal(
        graph="MiningOperationsSafetyGraph",
        sql=_sql(_FATIGUE_TO_INCIDENT_TMPL),
        params=("operator_id",),
        tables_read=_tables(
            "fatigue_logs_node", "operators_node",
            "operator_vehicle_assignments", "fleet_vehicles",
            "incident_involvements", "safety_incidents",
        ),
    ),
    "ontology_related": Traversal(
        graph="MiningOntologyGraph",
        sql=_sql(_ONTOLOGY_RELATED_TMPL),
        params=("concept",),
        tables_read=_tables("ontology_concepts", "ontology_triples"),
    ),
}

_ALL_TABLES: tuple[str, ...] = tuple(
    sorted({t for trav in TRAVERSALS.values() for t in trav.tables_read})
)


def make_graph_traverse(allowed: list[str]):
    """Build an enveloped graph_traverse bound to the traversals an agent owns."""
    if not allowed:
        raise ValueError(
            "allowed traversal list is empty; pass at least one traversal name"
        )
    unknown = [name for name in allowed if name not in TRAVERSALS]
    if unknown:
        raise ValueError(f"unknown traversal(s): {unknown}")
    tables: tuple[str, ...] = tuple(
        sorted({t for name in allowed for t in TRAVERSALS[name].tables_read})
    )

    @tool(list(tables))
    def graph_traverse(traversal: str, params: dict):
        """Run one of the canonical property-graph traversals."""
        if traversal not in allowed:
            raise ToolFailure(
                "TRAVERSAL_NOT_PERMITTED",
                f"this agent may run {sorted(allowed)}, not {traversal!r}",
                requested=traversal,
            )
        spec = TRAVERSALS[traversal]
        missing = [p for p in spec.params if p not in params]
        if missing:
            raise ToolFailure(
                "INVALID_ARGUMENT",
                f"traversal {traversal!r} requires {list(spec.params)}",
                missing=missing,
            )
        bound = {p: params[p] for p in spec.params}
        rows, scanned = run_query(spec.sql, bound, list(spec.tables_read))
        return {"graph": spec.graph, "rows": rows}, scanned

    return graph_traverse
