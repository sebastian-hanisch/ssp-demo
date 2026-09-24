"""Kern: Successive Shortest Paths gegen Handfälle und unabhängige Gegenproben (networkx, scipy, Brute Force), Invarianten je Runde aus dem Trace (gültige Potenziale, Preis = Schattenpreis von T,
nicht fallende Wegpreise, jeder Zwischenfluss kostenminimal für seine Menge), Zertifikat, Negativkontrolle, Kapazitäts-Skalierung."""

import itertools
import random

import networkx as nx
import numpy as np
import pytest
from scipy.optimize import linear_sum_assignment, linprog

import ssp_algorithm as ssp
import ssp_edmonds_karp as ek
import ssp_evaluation as ev
import ssp_scenario as sc
from ssp_scenario import SplitMix64


def _nets(count, sizes=((2, 2, 3), (3, 3, 6), (3, 3, 8), (4, 3, 5), (2, 4, 9), (6, 6, 12))):
    """Zufällige Distributionsnetze unterschiedlicher Größe, Dichte, Streuung und Auslastung."""
    rng = random.Random(13)
    for i in range(count):
        p, d, s = sizes[i % len(sizes)]
        yield sc.generate(p, d, s, rng.choice((20, 40, 60, 80, 100)), rng.choice((0, 25, 50, 75, 100)), rng.choice((40, 90, 120, 160)), 3000 + i)


def _digraph(net, demand=None):
    g = nx.DiGraph()
    g.add_nodes_from(range(net.n))
    for u, v, c, k, _ in net.arcs:
        g.add_edge(u, v, capacity=c, weight=k)
    if demand is not None:
        g.nodes[net.s]["demand"] = -demand
        g.nodes[net.t]["demand"] = demand
    return g


def _optimum(net, value=None):
    """(Wert, minimale Kosten): networkx, größter Fluss (value=None) oder Fluss der Menge `value`."""
    if value is None:
        g = _digraph(net)
        flow = nx.max_flow_min_cost(g, net.s, net.t)
        return sum(flow[net.s].values()), nx.cost_of_flow(g, flow)
    cost, _ = nx.network_simplex(_digraph(net, value))
    return value, cost


def _balance(net, flow):
    bal = [0] * net.n
    for i, (u, v, _, _, _) in enumerate(net.arcs):
        bal[u] -= flow[i]
        bal[v] += flow[i]
    return bal


def _is_flow(net, flow):
    bal = _balance(net, flow)
    return all(0 <= flow[i] <= net.arcs[i][2] for i in range(net.m)) and all(bal[v] == 0 for v in range(net.n) if v not in (net.s, net.t)) and bal[net.t] == -bal[net.s]


def test_splitmix64_reference_vector():
    rng = SplitMix64(0)
    assert [rng.next() for _ in range(2)] == [0xE220A8397B1DCDAF, 0x6E789E6AA1B965F4]


def test_the_edmonds_karp_copy_reproduces_the_predecessor_numbers():
    """Wache: die Kopie der Vorgänger-Demo liefert über die 100 festen Netze dieselben durchsuchten Kanten (Mittel 524,75) wie dort."""
    import ssp_constants as C
    scans = [ek.max_flow(sc.generate(3, 3, 8, 60, 50, 90, seed), "bfs", keep_flows=False).scanned_total for seed in C.DIST_SEEDS]
    assert sum(scans) == 52475


def test_diamond_takes_the_detour_over_a_back_arc():
    """Erste Einheit S-A-B-T (3), zweite S-B-A-T über die Rückkante B->A: 4 - 1 + 4 = 7; zusammen 10 - so viel wie S-A-T plus S-B-T."""
    net = sc.diamond_cost()
    r = ssp.ssp(net)
    assert [x.price for x in r.rounds] == [3, 7] and [x.uses_back_arc for x in r.rounds] == [False, True] and r.value == 2 and r.total == 10
    assert r.rounds[1].nodes == (0, 3, 2, 1) and r.rounds[1].path[1] % 2 == 1
    assert r.flow == (1, 1, 0, 1, 1)                                # die Kante A->B ist wieder leer


def test_brute_force_on_the_diamond():
    net = sc.diamond_cost()
    best = min(sum(f[i] * net.arcs[i][3] for i in range(net.m)) for f in itertools.product((0, 1), repeat=net.m) if _is_flow(net, f) and _balance(net, f)[net.t] == 2)
    assert best == 10 == ssp.ssp(net).total


@pytest.mark.parametrize("search", ["dijkstra", "spfa"])
def test_cost_and_value_equal_networkx_on_the_hundred_fixed_nets(search):
    import ssp_constants as C
    for seed in C.DIST_SEEDS:
        net = sc.generate(3, 3, 8, 60, 50, 90, seed)
        r = ssp.ssp(net, search)
        assert (r.value, r.total) == _optimum(net), (search, seed)


def test_cost_equals_networkx_on_varied_nets():
    for net in _nets(60):
        r = ssp.ssp(net)
        assert (r.value, r.total) == _optimum(net)
        assert _is_flow(net, r.flow) and ssp.flow_cost(net, r.flow) == r.total


def test_target_quantity_is_the_cheapest_flow_of_that_size():
    for net in _nets(40):
        top = ssp.ssp(net).value
        for target in sorted({max(1, top // 2), max(1, top * 4 // 5), top}):
            r = ssp.ssp(net, target=target)
            assert r.value == target and (r.value, r.total) == _optimum(net, target) and _is_flow(net, r.flow)


def test_a_target_beyond_the_maximum_stops_at_the_maximum():
    net = sc.generate(3, 3, 8, 60, 50, 160, 4)
    top = ssp.ssp(net).value
    assert ssp.ssp(net, target=top + 50).value == top


def test_every_intermediate_flow_is_cheapest_for_its_quantity():
    """Kern von SSP: nach jeder Runde ist der Fluss kostenminimal für seine Menge (unabhängig durch networkx bestätigt)."""
    for net in list(_nets(12)):
        for rnd in ssp.ssp(net).rounds:
            assert _is_flow(net, rnd.flow_after) and ssp.flow_cost(net, rnd.flow_after) == rnd.total == _optimum(net, rnd.value)[1]


def test_scipy_linear_program_agrees():
    """Min-Cost-Flow als LP (HiGHS): der Flusswert ist fest, die Kosten minimal."""
    for net in list(_nets(10)):
        r = ssp.ssp(net)
        m = net.m
        a_eq, b_eq = [], []
        for v in range(net.n):
            row = np.zeros(m)
            for i, (u, w, _, _, _) in enumerate(net.arcs):
                row[i] += (w == v) - (u == v)
            if v not in (net.s, net.t):
                a_eq.append(row)
                b_eq.append(0)
        row = np.array([1.0 if net.arcs[i][0] == net.s else 0.0 for i in range(m)])
        a_eq.append(row)
        b_eq.append(r.value)
        lp = linprog([a[3] for a in net.arcs], A_eq=np.array(a_eq), b_eq=b_eq, bounds=[(0, a[2]) for a in net.arcs], method="highs")
        assert lp.status == 0 and round(lp.fun) == r.total


def test_assignment_network_is_the_hungarian_method():
    net = sc.assignment_cost(5)
    cost = np.zeros((5, 5), dtype=int)
    for u, v, _, k, _ in net.arcs:
        if 2 <= u < 7 and 7 <= v < 12:
            cost[u - 2, v - 7] = k
    rows, cols = linear_sum_assignment(cost)
    r = ssp.ssp(net)
    assert r.total == cost[rows, cols].sum() == 10 and r.value == 5
    # jede Einheit hat Kapazität 1: die Flusskanten mit Fluss 1 zwischen den Reihen sind eine Zuordnung
    matched = [(net.arcs[i][0] - 2, net.arcs[i][1] - 7) for i in range(net.m) if r.flow[i] and 2 <= net.arcs[i][0] < 7 and 7 <= net.arcs[i][1] < 12]
    assert sorted(a for a, _ in matched) == list(range(5)) and sorted(b for _, b in matched) == list(range(5))


def test_prices_are_non_decreasing_and_cost_curve_is_convex():
    for net in _nets(40):
        rounds = ssp.ssp(net).rounds
        prices = [r.price for r in rounds]
        assert prices == sorted(prices)
        slopes = [r.price for r in rounds]
        assert all(a <= b for a, b in zip(slopes, slopes[1:]))            # Steigung der Kostenkurve steigt = konvex


def test_round_invariants_from_the_trace():
    """Je Runde: Potenziale gültig (reduzierte Kosten aller Restkanten >= 0), Preis = pi(T) - pi(S), Kosten = Preis x Engpass, die Kanten des Weges reduziert 0."""
    for net in _nets(40):
        r = ssp.ssp(net)
        prev_total = prev_value = 0
        for rnd in r.rounds:
            pi, flow = rnd.potentials, rnd.flow_after
            assert ev.proof(net, flow, pi)["valid"], "Potenziale ungültig"
            assert rnd.price == pi[net.t] - pi[net.s] and pi[net.s] == 0
            assert rnd.total == prev_total + rnd.bottleneck * rnd.price and rnd.value == prev_value + rnd.bottleneck
            for e in rnd.path:
                u, v, _, k, _ = net.arcs[e // 2]
                a, b = (u, v) if e % 2 == 0 else (v, u)
                assert (k if e % 2 == 0 else -k) + pi[a] - pi[b] == 0
            prev_total, prev_value = rnd.total, rnd.value
        assert (prev_value, prev_total) == (r.value, r.total)


def test_final_certificate_no_negative_cycle_and_complementary_slackness():
    for net in _nets(40):
        r = ssp.ssp(net)
        proof = ev.proof(net, r.flow, r.potentials)
        assert proof["valid"] and proof["worst"] is not None and proof["worst"] >= 0
        pi, ok = ssp.certificate(net, r.flow)
        assert ok and ev.proof(net, r.flow, pi)["valid"]
        # unabhängig: kein negativer Kreis im Restgraphen (networkx Bellman-Ford)
        g = nx.DiGraph()
        for i, (u, v, c, k, _) in enumerate(net.arcs):
            if c - r.flow[i] > 0:
                g.add_edge(u, v, weight=k)
            if r.flow[i] > 0:
                g.add_edge(v, u, weight=-k)
        assert not nx.negative_edge_cycle(g)


def test_a_non_optimal_flow_has_no_valid_certificate():
    net = sc.generate(3, 3, 8, 60, 50, 90, 155)
    flow = ek.max_flow(net, "bfs").flows[-1]
    assert ssp.flow_cost(net, flow) > ssp.ssp(net).total
    assert ssp.certificate(net, flow)[1] is False


def test_dijkstra_and_bellman_ford_agree_on_the_cost_curve():
    for net in _nets(40):
        a, b = ssp.ssp(net, "dijkstra"), ssp.ssp(net, "spfa")
        assert (a.value, a.total) == (b.value, b.total)
        assert all(ev.cost_at(a.rounds, x) == ev.cost_at(b.rounds, x) for x in range(a.value + 1))       # gleiche Grenzkosten je Einheit, nur Gleichstände dürfen anders liegen


def test_the_naive_search_is_right_on_the_diamond_and_wrong_on_some_nets():
    """Negativkontrolle: ohne Potenziale schließt Dijkstra Knoten zu früh ab. Nie besser als das Optimum, aber ein gültiger Fluss."""
    assert ssp.ssp(sc.diamond_cost(), "naive").total == 10
    wrong = 0
    for net in _nets(60):
        naive, best = ssp.ssp(net, "naive"), ssp.ssp(net)
        assert naive.total >= best.total and _is_flow(net, naive.flow)
        wrong += naive.total > best.total
    assert wrong >= 1
    net = sc.generate(3, 3, 8, 60, 50, 90, 170)
    naive, best = ssp.ssp(net, "naive"), ssp.ssp(net)
    assert (naive.total, best.total) == (1420, 1382) and ssp.certificate(net, naive.flow)[1] is False


def test_capacity_scaling_keeps_the_path_sequence_and_multiplies_value_and_cost():
    for net in _nets(20):
        base = ssp.ssp(net)
        for k in (10, 1000):
            big = ssp.ssp(sc.scale_capacities(net, k))
            assert [x.path for x in big.rounds] == [x.path for x in base.rounds] and (big.value, big.total) == (k * base.value, k * base.total)


def test_rounds_never_exceed_the_flow_value():
    for net in _nets(40):
        r = ssp.ssp(net)
        assert len(r.rounds) <= r.value


def test_unreachable_target_gives_zero_and_no_rounds():
    net = sc.generate(2, 6, 3, 20, 50, 90, 8)
    r = ssp.ssp(net)
    assert r.value == 0 and r.rounds == () and r.total == 0 and r.final_scanned > 0


def test_unknown_search_is_rejected():
    with pytest.raises(ValueError):
        ssp.ssp(sc.diamond_cost(), "astar")


def test_scanned_counts_add_up():
    net = sc.generate(3, 3, 8, 60, 50, 90, 155)
    r = ssp.ssp(net)
    assert r.scanned_total == sum(x.scanned for x in r.rounds) + r.final_scanned
