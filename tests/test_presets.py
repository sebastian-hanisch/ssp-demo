"""Presets: vollständig, in den Grenzen, und jedes Beispielnetz zeigt, was sein Hilfetext behauptet."""

import pytest

import ssp_algorithm as ssp
import ssp_constants as C
import ssp_evaluation as ev
import ssp_presets as P
import ssp_scenario as sc

KEYS = set(P.PRESET_KEYS)


def _net(p):
    return sc.build(p["net"], p["p"], p["d"], p["s"], p["density"], p["spread"], p["load"], p["seed"])


def _analyse(p):
    return ev.analyse(_net(p), p["search"], p["target"])


def test_every_preset_has_help_and_all_keys():
    assert set(C.PRESETS) == set(C.PRESET_HELP) and len(C.PRESETS) == 8
    assert all(C.PRESET_HELP[name].strip() for name in C.PRESETS)
    for name, p in C.PRESETS.items():
        assert set(p) == KEYS, name


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_preset_values_are_inside_the_bounds_and_on_the_step_grid(name):
    p = C.PRESETS[name]
    assert p["net"] in C.NETS and p["search"] in C.SEARCH_LABELS
    for key, state_key in P.PRESET_KEYS.items():
        spec = P.SETTING_SPECS[state_key]
        if spec.lo is not None:
            assert spec.lo <= p[key] <= spec.hi, (name, key)
    assert (p["density"] - C.DENSITY_MIN) % 10 == 0 and p["spread"] % 25 == 0 and (p["load"] - C.LOAD_MIN) % 10 == 0 and (p["target"] - C.TARGET_MIN) % 10 == 0


def test_setting_specs_have_room_to_move():
    """Ein Regler mit lo == hi würde Streamlit abstürzen lassen."""
    assert all(spec.lo < spec.hi for spec in P.SETTING_SPECS.values() if spec.lo is not None)


def test_presets_use_seeds_outside_the_distribution_set():
    for name, p in C.PRESETS.items():
        assert p["seed"] not in C.DIST_SEEDS, name


def test_defaults_equal_the_random_net_preset():
    p = C.PRESETS["🚚 Zufallsnetz"]
    assert (p["net"], p["search"], p["target"], p["p"], p["d"], p["s"], p["density"], p["spread"], p["load"], p["seed"]) == (
        C.DEFAULT_NET, C.DEFAULT_SEARCH, C.DEFAULT_TARGET, C.DEFAULT_P, C.DEFAULT_D, C.DEFAULT_S, C.DEFAULT_DENSITY, C.DEFAULT_SPREAD, C.DEFAULT_LOAD, C.DEFAULT_SEED)


def test_the_variant_presets_share_the_default_net():
    base = C.PRESETS["🚚 Zufallsnetz"]
    assert all(C.PRESETS["🐢 Bellman-Ford"][k] == base[k] for k in base if k != "search") and C.PRESETS["🐢 Bellman-Ford"]["search"] == "spfa"
    assert all(C.PRESETS["🎯 80 % der Menge"][k] == base[k] for k in base if k != "target") and C.PRESETS["🎯 80 % der Menge"]["target"] == 80
    assert all(C.PRESETS["🏭 Werke knapp"][k] == base[k] for k in base if k != "load") and all(C.PRESETS["🕸️ Dünnes Netz"][k] == base[k] for k in base if k != "density")


def test_fixed_presets_hide_the_random_controls():
    assert {n for n, p in C.PRESETS.items() if p["net"] in C.FIXED_NETS} == {"🔀 Raute mit Umleitung", "💑 Zuordnung mit Kosten"}


def test_default_net_is_a_typical_draw():
    """Das Beispielnetz liegt beim kostenblinden Aufschlag nahe am Median (±3 Prozentpunkte), liefert die ganze Nachfrage, hat 2 bis 5 Runden über Rückkanten und 10 bis 14 Runden."""
    p = C.PRESETS["🚚 Zufallsnetz"]
    dist = ev.distribution(p["p"], p["d"], p["s"], p["density"], p["spread"], p["load"])
    _, code, d = ev.verdict(_analyse(p))
    assert code == "optimal" and abs(d["ek_gap_pct"] - dist["ek_gap_median"]) <= 3 and d["value"] == d["demand"] and 2 <= d["back_rounds"] <= 5 and 10 <= d["rounds"] <= 14


def test_each_preset_shows_what_its_help_text_says():
    a = {name: _analyse(p) for name, p in C.PRESETS.items()}
    v = {name: ev.verdict(x) for name, x in a.items()}
    # Standardnetz: kostenminimal, EK um 11,9 % teurer
    d = v["🚚 Zufallsnetz"][2]
    assert (d["total"], d["ek_total"], d["ek_gap_pct"]) == (1197, 1339, 11.9) and d["back_rounds"] == 3 and d["rounds"] == 14
    # Bellman-Ford: dieselben Kosten, 1376 statt 824 durchsuchte Kanten (das 1,7-fache)
    b = v["🐢 Bellman-Ford"][2]
    assert b["total"] == d["total"] and (b["scanned"], d["scanned"]) == (1376, 824) and round(b["scanned"] / d["scanned"], 1) == 1.7
    # ohne Potenziale: 2,7 % teurer als nötig
    n = v["⚠️ Ohne Potenziale"]
    assert n[1] == "wrong" and n[2]["gap_pct"] == 2.7
    # 80 % der Menge kosten 74 % des Gesamtpreises
    t = a["🎯 80 % der Menge"]
    assert t.result.value == 61 and round(100 * t.result.total / 1197) == 74
    # Werke knapp: 89 von 118 Einheiten
    k = v["🏭 Werke knapp"][2]
    assert (k["value"], k["demand"]) == (89, 118)
    # Raute: Preise 3 und 7, zusammen 10; Zuordnung: 10 gegen 25 beim kostenblinden Fluss
    assert [r.price for r in a["🔀 Raute mit Umleitung"].result.rounds] == [3, 7] and a["🔀 Raute mit Umleitung"].result.total == 10
    z = v["💑 Zuordnung mit Kosten"][2]
    assert (z["total"], z["ek_total"]) == (10, 25)
    assert v["🕸️ Dünnes Netz"][2]["rounds"] < d["rounds"]


def test_the_presets_show_both_good_and_bad_news():
    """Gute Nachricht: SSP ist kostenminimal und billiger als der kostenblinde Fluss; schlechte: ohne Potenziale wird es teurer, Bellman-Ford durchsucht mehr Kanten, die Menge kann zu knapp sein."""
    a = {name: ev.verdict(_analyse(p)) for name, p in C.PRESETS.items()}
    assert a["🚚 Zufallsnetz"][1] == "optimal" and a["🚚 Zufallsnetz"][2]["ek_total"] > a["🚚 Zufallsnetz"][2]["total"]
    assert a["⚠️ Ohne Potenziale"][0] == "warning" and a["🏭 Werke knapp"][2]["value"] < a["🏭 Werke knapp"][2]["demand"]
    assert a["🐢 Bellman-Ford"][2]["scanned"] > a["🚚 Zufallsnetz"][2]["scanned"]
