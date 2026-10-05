"""Orakel: SSP auf beliebigen kleinen Netzen (Parallelkanten, Kapazität 0, Kosten 0, Schleifen) gegen ein lineares Programm (scipy/HiGHS):
Flusswert, Kosten, Kosten jedes Zwischenflusses und Gültigkeit der Potenziale."""

import random

import numpy as np
import pytest

import ssp_algorithm as ssp
import ssp_scenario as sc

linprog = pytest.importorskip("scipy.optimize").linprog


def _random_net(rng):
    n = rng.randint(2, 7)
    arcs = []
    for _ in range(rng.randint(1, 3 * n)):
        u, v = rng.randrange(n), rng.randrange(n)
        arcs.append((u, v, rng.choice([0, 1, 1, 2, 3, 5, 10]), rng.choice([0, 0, 1, 2, 5, 9]), sc.K_OTHER))
    names = tuple(str(i) for i in range(n))
    return sc.Net(names, names, tuple((0, 0) for _ in range(n)), tuple(arcs), 0, 1, False)


def _lp(net, value=None):
    """(Wert, minimale Kosten): größter Fluss bzw. Fluss der Menge `value`, als lineares Programm."""
    a = np.zeros((net.n, net.m))
    for i, (u, v, _, _, _) in enumerate(net.arcs):
        a[u, i] -= 1
        a[v, i] += 1
    inner = [v for v in range(net.n) if v not in (net.s, net.t)]
    bounds = [(0, arc[2]) for arc in net.arcs]
    if value is None:
        value = int(round(-linprog(-a[net.t], A_eq=a[inner], b_eq=np.zeros(len(inner)), bounds=bounds, method="highs").fun))
    r = linprog([arc[3] for arc in net.arcs], A_eq=np.vstack([a[inner], a[net.t]]), b_eq=np.append(np.zeros(len(inner)), value), bounds=bounds, method="highs")
    return value, int(round(r.fun))


def test_ssp_matches_linear_program_on_random_nets():
    rng = random.Random(5)
    for _ in range(60):
        net = _random_net(rng)
        value, opt = _lp(net)
        for search in ("dijkstra", "spfa"):
            r = ssp.ssp(net, search)
            assert (r.value, r.total) == (value, opt) and ssp.flow_cost(net, r.flow) == opt
        r = ssp.ssp(net)
        for ro in r.rounds[::2]:
            assert _lp(net, ro.value)[1] == ro.total
            pi = ro.potentials
            for i, (u, v, c, k, _) in enumerate(net.arcs):
                rc = k + pi[u] - pi[v]
                assert not (ro.flow_after[i] < c and rc < 0) and not (ro.flow_after[i] > 0 and rc > 0)
        if value > 1:
            half = value // 2
            assert ssp.ssp(net, "dijkstra", half).total == _lp(net, half)[1]
