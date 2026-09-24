"""Jede Zahl, die README und Hilfetexte nennen, ist hier belegt (Standardeinstellungen, 100 feste Netze, Seeds 100000-100099)."""

from pathlib import Path

import pytest

import ssp_algorithm as ssp
import ssp_constants as C
import ssp_evaluation as ev
import ssp_scenario as sc

S = (C.DEFAULT_P, C.DEFAULT_D, C.DEFAULT_S, C.DEFAULT_DENSITY, C.DEFAULT_SPREAD, C.DEFAULT_LOAD)


@pytest.fixture(scope="module")
def dist():
    return ev.distribution(*S)


def test_edmonds_karp_flow_is_a_clear_but_not_huge_amount_dearer(dist):
    """Vorgänger-Wache: Mittel 12,7 %, Median 11,1 % Mehrkosten des kostenblinden Flusses gegen den billigsten Fluss der gleichen Menge; nur 2 von 100 Netzen zufällig billigst."""
    assert dist["n_seeds"] == 100
    assert round(dist["ek_gap_mean"], 1) == 12.7 and round(dist["ek_gap_median"], 1) == 11.1
    assert dist["share_ek_optimal"] == 0.02 and round(dist["ek_gap_p90"], 1) == 24.3 and dist["ek_gap_max"] == 57.0


def test_ssp_never_costs_more_than_the_blind_flow_and_never_less_than_networkx():
    import networkx as nx
    for seed in C.DIST_SEEDS[:30]:
        net = sc.generate(*S, seed)
        g = nx.DiGraph()
        for u, v, c, k, _ in net.arcs:
            g.add_edge(u, v, capacity=c, weight=k)
        flow = nx.max_flow_min_cost(g, net.s, net.t)
        assert ssp.ssp(net).total == nx.cost_of_flow(g, flow)


def test_rounds_ssp_needs_slightly_more_than_edmonds_karp(dist):
    """Vorab-Vermutung 'SSP braucht mehr Runden, weil der billigste Weg nicht der kürzeste ist': stimmt, aber nur knapp (11,6 gegen 11,1; in 50 von 100 Netzen mehr, in 25 gleich viele)."""
    assert round(dist["rounds_mean"], 1) == 11.6 and round(dist["ek_rounds_mean"], 1) == 11.1 and dist["rounds_max"] == 18
    more = sum(1 for a, b in zip(dist["cols"]["rounds"], dist["cols"]["ek_rounds"]) if a > b)
    same = sum(1 for a, b in zip(dist["cols"]["rounds"], dist["cols"]["ek_rounds"]) if a == b)
    assert (more, same) == (50, 25)


def test_prices_of_the_paths_never_fall(dist):
    assert dist["share_monotone"] == 1.0


def test_price_of_the_last_unit(dist):
    """Vorab-Vermutung 'die letzte Einheit ist viel teurer als der Durchschnitt' abgeschwächt: im Mittel das 1,6-fache, höchstens das 2,4-fache; das letzte Zehntel der Menge kostet 15 % statt 10 %."""
    assert round(dist["ratio_last_mean"], 2) == 1.60 and round(dist["ratio_last_median"], 2) == 1.57 and round(dist["ratio_last_max"], 2) == 2.35
    assert round(100 * dist["share_last10_mean"]) == 15 and round(dist["last_price_mean"], 1) == 21.3 and round(dist["avg_price_mean"], 1) == 13.4


def test_back_arcs_are_used_in_every_net_with_a_typical_flow(dist):
    assert round(dist["back_rounds_mean"], 2) == 2.72 and dist["back_rounds_max"] == 10


def test_dijkstra_with_potentials_against_bellman_ford(dist):
    """Dijkstra mit Potenzialen 539 durchsuchte Kanten, Bellman-Ford 953 (das 1,8-fache), in 100 % der Netze höchstens so viele; beide mit denselben Kosten."""
    assert round(dist["dijkstra_mean"]) == 539 and round(dist["spfa_mean"]) == 953 and dist["dijkstra_median"] == 540 and dist["spfa_median"] == 923
    assert dist["share_dijkstra_le_spfa"] == 1.0 and dist["share_spfa_same"] == 1.0 and round(dist["spfa_mean"] / dist["dijkstra_mean"], 2) == 1.77


def test_scaling_slopes_and_ratios():
    rows = ev.scaling()
    slopes = ev.slopes(rows)
    assert round(slopes["dijkstra"], 2) == 1.69 and round(slopes["spfa"], 2) == 1.81
    ratios = [r["spfa"] / r["dijkstra"] for r in rows]
    assert round(min(ratios), 2) == 1.49 and round(max(ratios), 2) == 2.52 and ratios == sorted(ratios)          # der Abstand wächst mit dem Netz
    assert [round(r["m"]) for r in rows] == [16, 34, 73, 185, 431, 1168]


def test_naive_dijkstra_is_wrong_in_a_third_of_the_nets(dist):
    """32 von 100 Netzen: teurer als nötig, im Mittel dort 1,1 % (höchstens 3,8 %); Dijkstra ohne Potenziale durchsucht 565 Kanten, kaum mehr als mit Potenzialen (539)."""
    wrong = [g for g in dist["cols"]["naive_gap"] if g > 0]
    assert len(wrong) == 32 and dist["share_naive_wrong"] == 0.32
    assert round(sum(wrong) / len(wrong), 1) == 1.1 and max(wrong) == 3.8
    assert round(dist["naive_mean"]) == 565


def test_capacity_scaling_leaves_the_rounds_alone():
    rows = ev.capacity_table(*S)
    assert [r["rounds"] for r in rows] == [12.1] * 4 and [r["value"] for r in rows] == pytest.approx([65.6, 656, 6560, 65600])
    assert all(r["share_same"] == 1.0 for r in rows)


def test_only_a_fifth_of_the_nets_deliver_all_demand(dist):
    assert dist["share_all_served"] == 0.2


def test_default_net_numbers():
    a = ev.analyse(sc.generate(*S, C.DEFAULT_SEED))
    _, code, d = ev.verdict(a)
    assert code == "optimal" and (d["value"], d["demand"], d["total"], d["ek_total"], d["ek_gap_pct"], d["saving_pct"]) == (76, 76, 1197, 1339, 11.9, 10.6)
    assert (d["rounds"], d["ek_rounds"], d["back_rounds"], d["first_price"], d["last_price"], d["scanned"]) == (14, 12, 3, 11, 25, 824)
    assert round(d["avg_price"], 1) == 15.8


def test_eighty_percent_of_the_quantity_cost_74_percent():
    net = sc.generate(*S, C.DEFAULT_SEED)
    full, part = ssp.ssp(net), ssp.ssp(net, target=61)
    assert (part.value, part.total, full.total) == (61, 883, 1197) and round(100 * part.total / full.total) == 74 and round(100 * (full.total - part.total) / full.total) == 26


def test_assignment_and_diamond_numbers():
    a = ev.verdict(ev.analyse(sc.assignment_cost(5)))[2]
    assert (a["total"], a["ek_total"], a["ek_gap_pct"]) == (10, 25, 150.0) and a["back_rounds"] == 0
    d = ev.verdict(ev.analyse(sc.diamond_cost()))[2]
    assert d["prices"] == [3, 7] and d["total"] == 10 and d["back_rounds"] == 1


def test_the_extremes_of_the_input_ranges_keep_ssp_optimal():
    """Über die Ränder der Regler bleibt SSP gleich dem Optimum (networkx)."""
    import networkx as nx
    for args in ((2, 2, 3, 20, 0, 40), (6, 6, 12, 100, 100, 160), (2, 6, 12, 20, 100, 160), (6, 2, 3, 100, 0, 40)):
        net = sc.generate(*args, 5)
        g = nx.DiGraph()
        for u, v, c, k, _ in net.arcs:
            g.add_edge(u, v, capacity=c, weight=k)
        flow = nx.max_flow_min_cost(g, net.s, net.t)
        assert ssp.ssp(net).total == nx.cost_of_flow(g, flow)


def test_the_potential_update_needs_the_cap_at_the_distance_of_t():
    """README-Fallstrick: Zuwachs d(v) statt min(d(v), d(T)) macht die Potenziale in 39 von 40 Netzen ungültig (die Suche bricht bei T ab, dahinter sind die Entfernungen nur vorläufig)."""
    src = Path(ssp.__file__).read_text(encoding="utf-8")
    alt = src.replace("[min(dist[v], d) for v in range(n)]", "[dist[v] if dist[v] != INF else 0 for v in range(n)]")
    assert alt != src
    ns = {"__name__": "ssp_alt"}
    exec(compile(alt, "ssp_alt", "exec"), ns)
    bad = 0
    for seed in range(3000, 3040):
        net = sc.generate(*S, seed)
        bad += any(not ev.proof(net, r.flow_after, r.potentials)["valid"] for r in ns["ssp"](net).rounds)
    assert bad == 39
