"""Kennzahlen, Urteil und die Experimente der Demo (Verteilungen über feste Netze, Mehrkosten des Edmonds-Karp-Flusses, Preis der letzten Einheit, Suchen im Vergleich, ohne Potenziale, Kapazitäten).
Alles ganzzahlig gerechnet; Prozente entstehen erst bei der Ausgabe."""

from dataclasses import dataclass
from functools import lru_cache
from statistics import mean, median

import numpy as np

import ssp_algorithm as ssp
import ssp_constants as C
import ssp_edmonds_karp as ek
import ssp_scenario as sc

K_SUPPLY, K_LANE_IN, K_THROUGHPUT, K_LANE_OUT, K_DEMAND = sc.K_SUPPLY, sc.K_LANE_IN, sc.K_THROUGHPUT, sc.K_LANE_OUT, sc.K_DEMAND
STAGE_KINDS = (K_SUPPLY, K_LANE_IN, K_THROUGHPUT, K_LANE_OUT)


@dataclass(frozen=True)
class Analysis:
    net: sc.Net
    result: ssp.Result           # mit der gewählten Suche und Zielmenge
    optimum: ssp.Result          # Dijkstra mit Potenzialen, gleiche Zielmenge (die Messlatte; ohne Trace)
    edmonds_karp: ek.Result      # kostenblinder maximaler Fluss
    ek_cost: int
    max_value: int
    target: object               # None = maximaler Fluss
    demand: int
    stage_caps: dict
    search: str


def _demand(net):
    return sum(c for _, _, c, _, kind in net.arcs if kind == K_DEMAND)


def _stage_caps(net, cut_arcs):
    caps = {}
    for i in cut_arcs:
        kind = net.arcs[i][4]
        caps[kind] = caps.get(kind, 0) + net.arcs[i][2]
    return caps


def target_value(max_value, pct):
    """Zielmenge in Prozent des maximalen Flusses (aufgerundet); 100 % = None (so viel wie möglich)."""
    if pct >= 100:
        return None
    return max(1, -(-max_value * pct // 100))


def analyse(net, search=C.DEFAULT_SEARCH, target_pct=C.DEFAULT_TARGET):
    e = ek.max_flow(net, "bfs")
    target = target_value(e.value, target_pct)
    res = ssp.ssp(net, search, target)
    opt = res if search == "dijkstra" else ssp.ssp(net, "dijkstra", target, keep_trace=False)
    return Analysis(net, res, opt, e, ssp.flow_cost(net, e.flows[-1]), e.value, target, _demand(net) if net.logistic else 0, _stage_caps(net, e.cut_arcs), search)


def pct(numerator, denominator, digits=1):
    return round(100 * numerator / denominator, digits) if denominator else 0.0


def curve(rounds):
    """Kostenkurve: Punkte (Menge, Gesamtkosten) nach jeder Runde, beginnend bei (0, 0)."""
    return [(0, 0)] + [(r.value, r.total) for r in rounds]


def cost_at(rounds, x):
    """Gesamtkosten des billigsten Flusses der Menge x (stückweise linear zwischen den Runden)."""
    prev_v, prev_t = 0, 0
    for r in rounds:
        if x <= r.value:
            return prev_t + (x - prev_v) * r.price
        prev_v, prev_t = r.value, r.total
    return prev_t


def verdict(a):
    """(Stufe, Code, Daten): 'optimal' = kostenminimal, 'wrong' = die gewählte Suche liefert einen teureren Fluss, 'disconnected' = gar nichts kommt an."""
    res, net = a.result, a.net
    rounds = res.rounds
    prices = [r.price for r in rounds]
    data = {
        "value": res.value, "demand": a.demand, "max_value": a.max_value, "target": a.target, "share": pct(res.value, a.demand) if a.demand else None,
        "total": res.total, "optimal_total": a.optimum.total, "gap_pct": pct(res.total - a.optimum.total, a.optimum.total) if a.optimum.total else 0.0,
        "ek_total": a.ek_cost, "saving_pct": pct(a.ek_cost - a.optimum.total, a.ek_cost) if a.target is None else None,
        "ek_gap_pct": pct(a.ek_cost - a.optimum.total, a.optimum.total) if a.target is None and a.optimum.total else None,
        "rounds": len(rounds), "ek_rounds": len(a.edmonds_karp.rounds), "back_rounds": sum(1 for r in rounds if r.uses_back_arc), "scanned": res.scanned_total,
        "first_price": prices[0] if prices else 0, "last_price": prices[-1] if prices else 0, "avg_price": res.total / res.value if res.value else 0.0,
        "prices": prices, "stage_caps": a.stage_caps, "path_max": max((r.length for r in rounds), default=0),
    }
    if res.value == 0:
        return "warning", "disconnected", data
    if res.total > a.optimum.total:
        return "warning", "wrong", data
    return "success", "optimal", data


def _generate(p, d, s, density, spread, load, seed):
    return sc.generate(p, d, s, density, spread, load, seed)


@lru_cache(maxsize=128)
def _runs(p, d, s, density, spread, load, seeds=C.DIST_SEEDS):
    """Je Netz die drei Suchen und Edmonds-Karp (ohne Trace); von den Verteilungen gemeinsam genutzt."""
    out = []
    for seed in seeds:
        net = _generate(p, d, s, density, spread, load, seed)
        e = ek.max_flow(net, "bfs", keep_flows=False)
        out.append((net, _demand(net), {search: ssp.ssp(net, search, keep_trace=False) for search in ssp.SEARCHES}, e, ssp.flow_cost(net, e.flows[-1])))
    return out


@lru_cache(maxsize=256)
def distribution(p, d, s, density, spread, load, seeds=C.DIST_SEEDS):
    """Über feste Netze: Runden (SSP und Edmonds-Karp), Kosten (EK-Aufschlag), Wegpreise (nicht fallend, letzte Einheit), Suchen im Vergleich, ohne Potenziale."""
    keys = ("rounds", "ek_rounds", "ek_gap", "dijkstra", "spfa", "naive", "last_price", "avg_price", "ratio_last", "share_last10", "naive_gap", "back_rounds", "value")
    cols = {k: [] for k in keys}
    mono, naive_wrong, spfa_same, all_served = [], [], [], 0
    for net, demand, results, e, ek_cost in _runs(p, d, s, density, spread, load, seeds):
        r = results["dijkstra"]
        prices = [x.price for x in r.rounds]
        mono.append(all(a <= b for a, b in zip(prices, prices[1:])))
        opt = r.total
        cols["rounds"].append(len(r.rounds))
        cols["ek_rounds"].append(len(e.rounds))
        cols["ek_gap"].append(pct(ek_cost - opt, opt) if opt else 0.0)
        for name in ("dijkstra", "spfa", "naive"):
            cols[name].append(results[name].scanned_total)
        cols["last_price"].append(prices[-1] if prices else 0)
        cols["avg_price"].append(opt / r.value if r.value else 0.0)
        cols["ratio_last"].append(prices[-1] * r.value / opt if opt else 1.0)
        cols["share_last10"].append((opt - cost_at(r.rounds, 0.9 * r.value)) / opt if opt else 0.0)
        cols["naive_gap"].append(pct(results["naive"].total - opt, opt) if opt else 0.0)
        cols["back_rounds"].append(sum(1 for x in r.rounds if x.uses_back_arc))
        cols["value"].append(r.value)
        naive_wrong.append(results["naive"].total > opt)
        spfa_same.append(results["spfa"].total == opt)
        all_served += r.value == demand
    n = len(seeds)
    out = {"n_seeds": n, "cols": cols, "share_monotone": sum(mono) / n, "share_naive_wrong": sum(naive_wrong) / n, "share_spfa_same": sum(spfa_same) / n, "share_all_served": all_served / n,
           "share_ek_optimal": sum(1 for g in cols["ek_gap"] if g == 0) / n, "edges_mean": mean(net.m for net, *_ in _runs(p, d, s, density, spread, load, seeds)),
           "nodes_mean": mean(net.n for net, *_ in _runs(p, d, s, density, spread, load, seeds)), "ek_gap_p90": float(np.percentile(cols["ek_gap"], 90)),
           "share_dijkstra_le_spfa": sum(1 for a, b in zip(cols["dijkstra"], cols["spfa"]) if a <= b) / n}
    for k in keys:
        out[k + "_mean"], out[k + "_median"], out[k + "_max"] = mean(cols[k]), median(cols[k]), max(cols[k])
    return out


@lru_cache(maxsize=32)
def scaling(sizes=C.SCALE_SIZES, seeds=C.SCALE_SEEDS):
    """Durchsuchte Kanten gegen die Netzgröße: Dijkstra mit Potenzialen, Bellman-Ford, dazu die Runden."""
    rows = []
    for (p, d, s) in sizes:
        cols = {k: [] for k in ("dijkstra", "spfa", "rounds", "n", "m")}
        for seed in seeds:
            net = _generate(p, d, s, C.DEFAULT_DENSITY, C.DEFAULT_SPREAD, C.DEFAULT_LOAD, seed)
            a = ssp.ssp(net, "dijkstra", keep_trace=False)
            cols["dijkstra"].append(a.scanned_total)
            cols["spfa"].append(ssp.ssp(net, "spfa", keep_trace=False).scanned_total)
            cols["rounds"].append(len(a.rounds))
            cols["n"].append(net.n)
            cols["m"].append(net.m)
        rows.append({"size": (p, d, s), **{k: mean(v) for k, v in cols.items()}})
    return rows


def slopes(rows):
    x = np.log([r["m"] for r in rows])
    return {k: float(np.polyfit(x, np.log([r[k] for r in rows]), 1)[0]) for k in ("dijkstra", "spfa")}


@lru_cache(maxsize=16)
def capacity_table(p, d, s, density, spread, load, factors=C.CAPACITY_FACTORS, seeds=C.SCALE_SEEDS):
    """Kapazitäten mal k: Zahl der Runden bleibt gleich, Flusswert und Kosten wachsen mit k (dieselben Wege in derselben Reihenfolge)."""
    base = [(sc_net := _generate(p, d, s, density, spread, load, seed), ssp.ssp(sc_net, "dijkstra", keep_trace=False)) for seed in seeds]
    rows = []
    for k in factors:
        rounds, values, totals, same = [], [], [], 0
        for net, r0 in base:
            rk = ssp.ssp(sc.scale_capacities(net, k), "dijkstra", keep_trace=False)
            rounds.append(len(rk.rounds))
            values.append(rk.value)
            totals.append(rk.total)
            same += [x.path for x in rk.rounds] == [x.path for x in r0.rounds]
        rows.append({"k": k, "rounds": mean(rounds), "value": mean(values), "total": mean(totals), "share_same": same / len(base)})
    return rows


def proof(net, flow, pi):
    """Optimalitätsprüfung mit Potenzialen pi: jede Restkante hat reduzierte Kosten >= 0 (Vorwärtsrest: c + pi(u) - pi(v) >= 0; Rückkante mit Fluss: <= 0 auf der Vorwärtskante).
    Rückgabe: geprüfte Restkanten, Verletzungen, Kanten mit Fluss (`flow_arcs`) und davon die mit reduzierten Kosten 0 (`tight`; jede nicht volle Flusskante gehört dazu, die übrigen sind voll), kleinste reduzierte Kosten einer Vorwärts-Restkante."""
    checked = violations = tight = flow_arcs = 0
    worst = None
    for i, (u, v, cap, cost, _) in enumerate(net.arcs):
        rc = cost + pi[u] - pi[v]
        if flow[i] < cap:
            checked += 1
            violations += rc < 0
            worst = rc if worst is None else min(worst, rc)
        if flow[i] > 0:
            checked += 1
            violations += rc > 0
            flow_arcs += 1
            tight += rc == 0
    return {"valid": violations == 0, "checked": checked, "violations": violations, "tight": tight, "flow_arcs": flow_arcs, "worst": worst}
