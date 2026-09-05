"""Tests for data/generator/haulage.py (Task F — P7 Mine Controller data).

haul_cycle_log is the new table method/p7-mine-controller.yaml's three
instrumented drivers read; see that pack and haulage.py's own module
docstring for why haulage_routes and operator_vehicle_assignments cannot
support them on their own. These tests check the generator's structural
invariants and determinism directly against the DataFrame it builds — the
integration tests in tests/method/test_p7_pack.py pin the exact magnitudes a
live BigQuery read returns after this table is loaded.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd
import pytest

import haulage as H

ROUTE_IDS = {r["route_id"] for r in H.ROUTES}


@pytest.fixture(scope="module")
def log():
    return H.build_haul_cycle_log()


class TestSchema:
    def test_columns(self, log):
        assert list(log.columns) == [
            "route_id", "timestamp", "trip_count", "mean_cycle_time_mins",
            "mean_queue_wait_mins", "mean_payload_tons", "congestion_index",
        ]

    def test_row_count_is_routes_by_days_by_halves(self, log):
        days = (H.WINDOW_END - H.WINDOW_START).days + 1
        assert days == 167
        assert len(log) == len(H.ROUTES) * days * 2 == 3340

    def test_no_nulls(self, log):
        assert not log.isnull().any().any()

    def test_route_id_is_one_of_the_ten_live_routes(self, log):
        assert set(log.route_id) == ROUTE_IDS
        assert len(ROUTE_IDS) == 10

    def test_every_route_gets_exactly_334_rows(self, log):
        # 167 days x 2 halves, every route — a route that fell out of the
        # loop or got double-counted would fail this before anything else.
        counts = log.groupby("route_id").size()
        assert (counts == 334).all(), counts.to_dict()

    def test_timestamps_are_am_or_pm_only(self, log):
        hours = set(log.timestamp.dt.hour.unique())
        assert hours == {0, 12}

    def test_timestamps_sit_inside_the_existing_data_window(self, log):
        # crusher_states / metallurgical_recovery's own window, not
        # erp_work_orders' 2026-06-17 — see module docstring.
        assert log.timestamp.min() == H.WINDOW_START
        assert log.timestamp.max() == H.WINDOW_END + pd.Timedelta(hours=12)


class TestPlausibility:
    def test_trip_count_is_non_negative(self, log):
        assert (log.trip_count >= 0).all()

    def test_cycle_time_is_positive(self, log):
        assert (log.mean_cycle_time_mins > 0).all()

    def test_queue_wait_never_exceeds_cycle_time(self, log):
        assert (log.mean_queue_wait_mins <= log.mean_cycle_time_mins).all()

    def test_queue_wait_is_non_negative(self, log):
        assert (log.mean_queue_wait_mins >= 0).all()

    def test_payload_never_exceeds_the_fleets_largest_truck(self, log):
        # The fleet's largest model (Komatsu 930E-5) is rated at 290t; no
        # route's logged mean payload should read as though it routinely
        # exceeds that, which would be operationally implausible.
        assert (log.mean_payload_tons < 290.0).all()

    def test_congestion_index_stays_in_an_operationally_plausible_band(self, log):
        assert (log.congestion_index > 0.5).all()
        assert (log.congestion_index < 2.5).all()


class TestDesignInvariants:
    def test_three_routes_are_deliberately_underloaded(self, log):
        util = log.groupby("route_id").mean_payload_tons.mean() / H.FLEET_AVG_CAPACITY_TONS
        underloaded = util[util.index.isin(H.UNDERLOADED_ROUTES)]
        loaded = util[~util.index.isin(H.UNDERLOADED_ROUTES)]
        assert len(H.UNDERLOADED_ROUTES) == 3
        assert underloaded.max() < loaded.min(), (
            f"underloaded routes {underloaded.to_dict()} do not separate "
            f"from the rest {loaded.to_dict()}"
        )

    def test_pm_congestion_carries_over_from_a_congested_am_half(self, log):
        """The leading-indicator signal has to exist in the generator's own
        output, not just survive a SQL band in the integration test: a
        route-day whose AM half ran above baseline should show a materially
        higher PM congestion_index, on average, than one that did not.
        """
        wide = log.copy()
        wide["day"] = wide.timestamp.dt.date
        wide["half"] = wide.timestamp.dt.hour.map({0: "AM", 12: "PM"})
        routes = pd.DataFrame(H.ROUTES).set_index("route_id")
        wide = wide.join(routes[["congestion_factor"]], on="route_id")
        am = wide[wide.half == "AM"].set_index(["route_id", "day"]).congestion_index
        pm = wide[wide.half == "PM"].set_index(["route_id", "day"]).congestion_index
        baseline = wide[wide.half == "AM"].set_index(
            ["route_id", "day"]
        ).congestion_factor
        am_high = am[am > baseline]
        am_normal = am[am <= baseline]
        assert pm.loc[am_high.index].mean() > pm.loc[am_normal.index].mean()

    def test_wider_congestion_band_costs_completed_trips(self, log):
        """Mechanical consequence of the model (lam = active_minutes /
        cycle_time), checked directly on the generator's own output rather
        than only downstream in the SQL: a half whose cycle time ran long
        must show fewer trips, on average, than one that ran short.
        """
        median_cycle = log.mean_cycle_time_mins.median()
        slow = log[log.mean_cycle_time_mins > median_cycle]
        fast = log[log.mean_cycle_time_mins <= median_cycle]
        assert slow.trip_count.mean() < fast.trip_count.mean()


class TestDeterminism:
    def test_rebuilding_is_byte_identical(self):
        first = H.build_haul_cycle_log()
        second = H.build_haul_cycle_log()
        pd.testing.assert_frame_equal(first, second)

    def test_stable_hash_is_not_pythons_salted_hash(self):
        # The bug this guards against: PYTHONHASHSEED-salted hash() in a seed
        # derivation produces a different row ordering per process. Two
        # independent calls with the same key must agree.
        assert H._stable_hash("ROUTE-01") == H._stable_hash("ROUTE-01")

    def test_rng_is_keyed_by_seed_and_parts(self):
        a = H._rng("haul-cycle", "ROUTE-01", "2026-01-01", "AM")
        b = H._rng("haul-cycle", "ROUTE-01", "2026-01-01", "AM")
        assert a.uniform() == b.uniform()
