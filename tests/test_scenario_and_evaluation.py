"""Szenario (Aufbau, Reproduzierbarkeit, Stufen, Lehrnetze), Auswertung (Urteil, Verteilungen, Kostenkurve, Skalierung, Kapazitäten)."""

import pytest

import ssp_algorithm as ssp
import ssp_constants as C
import ssp_edmonds_karp as ek
import ssp_evaluation as ev
import ssp_scenario as sc

DEFAULT = (C.DEFAULT_P, C.DEFAULT_D, C.DEFAULT_S, C.DEFAULT_DENSITY, C.DEFAULT_SPREAD, C.DEFAULT_LOAD)


def _net(seed=C.DEFAULT_SEED, *settings):
    return sc.generate(*(settings or DEFAULT), seed)


def test_generation_is_reproducible_and_seed_dependent():
    assert _net(5) == _net(5) and _net(5) != _net(6)


def test_structure_of_a_distribution_net():
    p, d, s = 3, 3, 8
    net = _net()
    assert net.n == 2 + p + 2 * d + s and net.s == 0 and net.t == 1 and net.logistic
    kinds = [a[4] for a in net.arcs]
    assert kinds.count(sc.K_SUPPLY) == p and kinds.count(sc.K_THROUGHPUT) == d and kinds.count(sc.K_DEMAND) == s
    assert all(a[2] >= 1 for a in net.arcs)
    for u, v, _, _, kind in net.arcs:
        assert net.pos[u][1] > net.pos[v][1]


def test_costs_lie_in_the_documented_ranges():
    for seed in range(20):
        for u, v, _, cost, kind in _net(seed).arcs:
            lo, hi = {sc.K_SUPPLY: (1, 5), sc.K_LANE_IN: (1, 9), sc.K_THROUGHPUT: (1, 3), sc.K_LANE_OUT: (1, 9), sc.K_DEMAND: (0, 0)}[kind]
            assert lo <= cost <= hi


@pytest.mark.parametrize("seed", range(20))
def test_every_plant_and_store_has_a_lane_even_on_the_thinnest_net(seed):
    net = _net(seed, 3, 3, 8, C.DENSITY_MIN, C.DEFAULT_SPREAD, C.DEFAULT_LOAD)
    assert {a[1] for a in net.arcs if a[4] == sc.K_SUPPLY} <= {a[0] for a in net.arcs if a[4] == sc.K_LANE_IN}
    assert {a[0] for a in net.arcs if a[4] == sc.K_DEMAND} <= {a[1] for a in net.arcs if a[4] == sc.K_LANE_OUT}


def test_a_thinner_net_only_removes_lanes_and_keeps_all_other_values():
    for seed in range(20):
        thin, full = _net(seed, 3, 3, 8, 40, 50, 90), _net(seed, 3, 3, 8, 100, 50, 90)
        assert set(thin.arcs) <= set(full.arcs) and len(thin.arcs) < len(full.arcs)


def test_teaching_nets_and_build_ignore_the_random_settings():
    assert not sc.assignment_cost(5).logistic and sc.build("assignment", 6, 6, 12, 100, 100, 160, 1) == sc.assignment_cost(5)
    assert sc.build("diamond", 6, 6, 12, 100, 100, 160, 1) == sc.diamond_cost()
    assert sc.build("random", *DEFAULT, 9) == _net(9)


def test_teaching_nets_have_the_documented_shape():
    d = sc.diamond_cost()
    assert d.n == 4 and d.m == 5 and [a[2] for a in d.arcs] == [1] * 5 and [a[3] for a in d.arcs] == [1, 4, 1, 4, 1]
    a = sc.assignment_cost(5)
    assert a.n == 12 and a.m == 35 and all(x[2] == 1 for x in a.arcs) and {x[3] for x in a.arcs if 2 <= x[0] < 7} <= set(range(1, 10))


def test_scale_capacities_multiplies_capacities_only():
    net = _net()
    big = sc.scale_capacities(net, 7)
    assert [(a[0], a[1], a[3], a[4]) for a in big.arcs] == [(a[0], a[1], a[3], a[4]) for a in net.arcs] and [a[2] for a in big.arcs] == [7 * a[2] for a in net.arcs]


def test_verdict_codes():
    lvl, code, d = ev.verdict(ev.analyse(_net(1, 3, 3, 8, 100, 50, 40), "dijkstra", 100))
    assert (lvl, code) == ("success", "optimal") and d["value"] == d["demand"]
    lvl, code, d = ev.verdict(ev.analyse(_net(1, 3, 3, 8, 60, 50, 160), "dijkstra", 100))
    assert (lvl, code) == ("success", "optimal") and d["value"] < d["demand"] and set(d["stage_caps"]) & set(ev.STAGE_KINDS)
    lvl, code, d = ev.verdict(ev.analyse(_net(170), "naive", 100))
    assert (lvl, code) == ("warning", "wrong") and d["total"] > d["optimal_total"] and d["gap_pct"] == 2.7
    lvl, code, d = ev.verdict(ev.analyse(sc.generate(2, 6, 3, 20, 50, 90, 8), "dijkstra", 100))
    assert (lvl, code) == ("warning", "disconnected") and d["value"] == 0
    assert ev.verdict(ev.analyse(sc.diamond_cost(), "spfa", 100))[:2] == ("success", "optimal")


def test_verdict_data_is_consistent():
    a = ev.analyse(_net())
    _, _, d = ev.verdict(a)
    assert d["rounds"] == len(a.result.rounds) == len(d["prices"]) and d["scanned"] == a.result.scanned_total
    assert d["ek_total"] == ssp.flow_cost(a.net, ek.max_flow(a.net, "bfs").flows[-1]) and d["ek_rounds"] == len(ek.max_flow(a.net, "bfs", keep_flows=False).rounds)
    assert d["ek_total"] >= d["optimal_total"] == d["total"] and d["first_price"] == d["prices"][0] and d["last_price"] == d["prices"][-1]
    assert d["back_rounds"] == sum(1 for r in a.result.rounds if r.uses_back_arc)


def test_target_percent_maps_to_a_quantity_and_only_the_full_flow_has_an_edmonds_karp_comparison():
    net = _net()
    a = ev.analyse(net, "dijkstra", 80)
    assert a.target == ev.target_value(a.max_value, 80) and a.result.value == a.target < a.max_value
    assert ev.verdict(a)[2]["ek_gap_pct"] is None and ev.verdict(ev.analyse(net, "dijkstra", 100))[2]["ek_gap_pct"] is not None
    assert ev.target_value(10, 100) is None and ev.target_value(10, 20) == 2 and ev.target_value(3, 20) == 1


def test_cost_at_interpolates_the_cost_curve():
    rounds = ssp.ssp(_net()).rounds
    for r in rounds:
        assert ev.cost_at(rounds, r.value) == r.total
    assert ev.cost_at(rounds, 0) == 0 and ev.cost_at(rounds, rounds[-1].value + 5) == rounds[-1].total
    first = rounds[0]
    assert ev.cost_at(rounds, first.bottleneck - 1) == (first.bottleneck - 1) * first.price
    assert ev.curve(rounds)[0] == (0, 0) and ev.curve(rounds)[-1] == (rounds[-1].value, rounds[-1].total)


def test_distribution_is_consistent_with_single_runs():
    seeds = tuple(range(5))
    dist = ev.distribution(*DEFAULT, seeds=seeds)
    runs = [ssp.ssp(sc.generate(*DEFAULT, s), "dijkstra", keep_trace=False) for s in seeds]
    assert dist["cols"]["dijkstra"] == [r.scanned_total for r in runs] and dist["cols"]["rounds"] == [len(r.rounds) for r in runs]
    assert dist["cols"]["spfa"] == [ssp.ssp(sc.generate(*DEFAULT, s), "spfa", keep_trace=False).scanned_total for s in seeds]
    assert dist["n_seeds"] == 5 and 0 <= dist["share_all_served"] <= 1 and dist["share_monotone"] == 1.0
    assert all(g >= 0 for g in dist["cols"]["ek_gap"]) and all(g >= 0 for g in dist["cols"]["naive_gap"])


def test_scaling_and_capacity_rows():
    rows = ev.scaling()
    assert [r["size"] for r in rows] == list(C.SCALE_SIZES) and all(r["dijkstra"] > 0 and r["spfa"] > r["dijkstra"] for r in rows)
    assert all(0.5 < s < 2.5 for s in ev.slopes(rows).values())
    cap = ev.capacity_table(*DEFAULT)
    assert [r["k"] for r in cap] == list(C.CAPACITY_FACTORS)
    assert all(r["rounds"] == cap[0]["rounds"] and r["share_same"] == 1.0 and r["value"] == pytest.approx(r["k"] * cap[0]["value"]) and r["total"] == pytest.approx(r["k"] * cap[0]["total"]) for r in cap)


def test_proof_helper_counts_and_detects_violations():
    net = sc.diamond_cost()
    r = ssp.ssp(net)
    p = ev.proof(net, r.flow, r.potentials)
    assert p["valid"] and p["violations"] == 0 and p["tight"] == 2 and p["flow_arcs"] == 4 and p["checked"] == 1 + 4        # eine Kante mit Rest, vier Kanten mit Fluss (S-B und A-T straff, S-A und B-T voll)
    assert not ev.proof(net, r.flow, tuple(0 for _ in range(net.n)))["valid"]                       # Potenziale 0 sind hier ungültig
