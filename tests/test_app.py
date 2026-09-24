"""Rauchtests der Streamlit-Oberfläche per AppTest: Standard, jedes Preset, alle drei Suchen, Zielmenge-Randwerte, Randgrößen, Schritt-Zustand, ausgeblendete Regler, Permalink, Experimente auf Abruf, Schlüssel und Achsensperre."""

import re
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import ssp_constants as C
import ssp_evaluation as ev
import ssp_scenario as sc
from ssp_presets import PRESET_KEYS

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app.py"

DEFAULT_TEXT = "Kostenminimal: Menge 76 kostet 1197 (15,8 je Einheit, von 11 für die erste bis 25 für die letzte). Die gesamte Nachfrage wird geliefert. Der kostenblinde Fluss von Edmonds-Karp wäre 11,9 % teurer (1339)."
# Anfang der Meldung zum gezeigten Netz (Streamlit legt das führende Emoji in `icon`, nicht in `value`)
EXPECTED = {
    "🚚 Zufallsnetz": DEFAULT_TEXT,
    "🐢 Bellman-Ford": DEFAULT_TEXT,
    "⚠️ Ohne Potenziale": "**Nicht kostenminimal:** Dijkstra ohne Potenziale liefert Menge 78 für 1420, der billigste Fluss dieser Menge kostet 1382 - der Fluss ist 2,7 % teurer als nötig.",
    "🎯 80 % der Menge": "Kostenminimal: Menge 61 kostet 883 (14,5 je Einheit, von 11 für die erste bis 19 für die letzte). Ein Fluss der Menge 61 kostet mindestens 883 - billiger geht es nicht.",
    "🏭 Werke knapp": "Kostenminimal: Menge 89 kostet 1403 (15,8 je Einheit, von 11 für die erste bis 21 für die letzte). Das Netz schafft höchstens 89 von 118 Einheiten (75 %)",
    "🕸️ Dünnes Netz": "Kostenminimal: Menge 67 kostet 900 (13,4 je Einheit, von 8 für die erste bis 21 für die letzte). Das Netz schafft höchstens 67 von 76 Einheiten (88 %)",
    "🔀 Raute mit Umleitung": "Kostenminimal: Menge 2 kostet 10 (5,0 je Einheit, von 3 für die erste bis 7 für die letzte). Der Fluss von Edmonds-Karp ist hier zufällig genauso billig.",
    "💑 Zuordnung mit Kosten": "Kostenminimal: Menge 5 kostet 10 (2,0 je Einheit, von 1 für die erste bis 4 für die letzte). Der kostenblinde Fluss von Edmonds-Karp wäre 150,0 % teurer (25).",
}


def _run(setup=None, timeout=600):
    at = AppTest.from_file(str(APP), default_timeout=timeout)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    if setup is not None:
        setup(at)
        at.run()
        assert not at.exception, [e.value for e in at.exception]
    return at


def _apply(at, p):
    for key, state_key in PRESET_KEYS.items():
        at.session_state[state_key] = p[key]


def _labels(at):
    return {w.label for w in list(at.sidebar.slider) + list(at.sidebar.selectbox) + list(at.sidebar.number_input) + list(at.sidebar.radio)}


def _texts(at):
    return [e.value for e in list(at.success) + list(at.warning) + list(at.info)]


def _has(at, prefix):
    return any(t.startswith(prefix) for t in _texts(at))


def _step(at):
    found = [s for s in at.slider if s.key == "ssp_step"]
    return found[0] if found else None


def _metric(at, label):
    return [m.value for m in at.metric if m.label == label]


def _captions(at):
    return [c.value for c in at.caption]


def test_default_renders_without_exception():
    at = _run()
    assert any("Runden in Aktion" in m.value for m in at.markdown)
    assert _has(at, EXPECTED["🚚 Zufallsnetz"]) and not at.error
    assert _metric(at, "Menge")[0] == "76 von 76" and _metric(at, "Gesamtkosten")[0] == "1197" and _metric(at, "Preis der letzten Einheit")[0] == "25" and _metric(at, "Durchsuchte Kanten")[0] == "824"


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_every_preset_renders_with_its_verdicts(name):
    at = _run(lambda a: _apply(a, C.PRESETS[name]))
    assert _has(at, EXPECTED[name]), _texts(at)
    if C.PRESETS[name]["net"] in C.FIXED_NETS:
        assert any(t.startswith("Festes Netz") for t in _texts(at))
    else:
        assert any(t.startswith("**Nicht nur dieses eine Netz:**") for t in [m.value for m in at.markdown])


@pytest.mark.parametrize("search", list(C.SEARCH_LABELS))
def test_every_search_renders_and_the_proof_frame_tells_optimal_from_wrong(search):
    at = _run(lambda a: a.session_state.__setitem__("search_radio", search))
    assert not at.error
    proof = " ".join(_captions(at))
    if search == "naive":                              # Standardnetz: die naive Suche ist hier zufällig richtig, auf dem Netz von Seed 170 nicht
        assert "Kein gültiges Potenzial" not in proof
        at = _run(lambda a: (a.session_state.__setitem__("search_radio", search), a.session_state.__setitem__("seed_input", 170)))
        assert "Kein gültiges Potenzial" in " ".join(_captions(at)) and _has(at, "**Nicht kostenminimal:**")
    else:
        assert "beweisen die Optimalität" in proof


@pytest.mark.parametrize("target", [C.TARGET_MIN, 50, 90, C.TARGET_MAX])
def test_target_quantity_edges_render(target):
    at = _run(lambda a: a.session_state.__setitem__("target_slider", target))
    assert not at.error
    _, code, dat = ev.verdict(ev.analyse(sc.generate(3, 3, 8, 60, 50, 90, C.DEFAULT_SEED), "dijkstra", target))
    assert code == "optimal" and _metric(at, "Menge")[0].startswith(str(dat["value"]))
    if target < 100:
        assert _has(at, "Kostenminimal: Menge") and any("billiger geht es nicht" in t for t in _texts(at))


def test_extreme_sizes_render():
    for p, d, s, dens, spread, load in ((C.P_MIN, C.D_MIN, C.S_MIN, C.DENSITY_MIN, C.SPREAD_MIN, C.LOAD_MIN), (C.P_MAX, C.D_MAX, C.S_MAX, C.DENSITY_MAX, C.SPREAD_MAX, C.LOAD_MAX),
                                        (C.P_MIN, C.D_MAX, C.S_MAX, C.DENSITY_MIN, C.SPREAD_MAX, C.LOAD_MAX), (C.P_MAX, C.D_MIN, C.S_MIN, C.DENSITY_MAX, C.SPREAD_MIN, C.LOAD_MIN)):
        def setup(at, vals=(p, d, s, dens, spread, load)):
            for key, value in zip(("p_slider", "d_slider", "s_slider", "density_slider", "spread_slider", "load_slider"), vals):
                at.session_state[key] = value
        at = _run(setup)
        step = _step(at)
        assert step is not None and step.value == step.max


def test_a_net_where_nothing_arrives_renders_and_says_so():
    """Zwei Werke, sechs Verteilzentren, drei Filialen, dünnes Netz: kein Weg von S nach T, die erste Suche scheitert sofort."""
    def setup(at):
        for key, value in (("p_slider", 2), ("d_slider", 6), ("s_slider", 3), ("density_slider", 20), ("spread_slider", 50), ("load_slider", 90), ("seed_input", 8)):
            at.session_state[key] = value
    at = _run(setup)
    assert _has(at, "Es kommt gar nichts an") and _metric(at, "Menge")[0].startswith("0 von ")
    assert _step(at).max == 1 and _step(at).value == 1                          # leerer Fluss und Beweis, keine Runde


def test_hidden_controls_follow_the_net():
    def labels_for(net):
        return _labels(_run(lambda a: a.session_state.__setitem__("net_select", net)))
    random_labels, fixed = labels_for("random"), labels_for("diamond")
    assert {"Netz", "Suche nach dem billigsten Weg", "Zielmenge [% des maximalen Flusses]", "Werke", "Verteilzentren", "Filialen", "Netzdichte [%]", "Streuung der Lane-Breiten [%]", "Auslastung [% der Werkskapazität]", "Zufalls-Seed"} <= random_labels
    assert fixed == {"Netz", "Suche nach dem billigsten Weg", "Zielmenge [% des maximalen Flusses]"}         # keine toten Regler bei festen Netzen


def test_hidden_slider_values_come_back_when_the_random_net_is_shown_again():
    at = _run(lambda a: a.session_state.__setitem__("density_slider", 80))
    at.session_state["net_select"] = "diamond"
    at.run()
    at.session_state["net_select"] = "random"
    at.run()
    assert not at.exception and at.slider(key="density_slider").value == 80


def test_step_slider_returns_to_the_last_frame_when_the_net_changes():
    at = _run()
    assert _step(at).max == 15 and _step(at).value == 15                       # leerer Fluss + 14 Runden + Beweis
    _step(at).set_value(4)
    at.run()
    assert _step(at).value == 4
    at.session_state["net_select"] = "diamond"
    at.run()
    assert not at.exception and _step(at).value == 3 == _step(at).max


def test_step_captions_for_start_rounds_back_arc_target_and_proof():
    at = _run()
    for k, needle in ((0, "Alle Potenziale sind 0"), (1, "Billigster Weg:"), (1, "Der Schattenpreis von T ist jetzt"), (15, "beweisen die Optimalität")):
        _step(at).set_value(k)
        at.run()
        assert not at.exception and any(needle in c for c in _captions(at)), (k, needle)
    at = _run(lambda a: a.session_state.__setitem__("net_select", "diamond"))
    _step(at).set_value(2)
    at.run()
    assert any("über eine Rückkante zurück" in c for c in _captions(at))
    at = _run(lambda a: a.session_state.__setitem__("target_slider", 80))
    last = _step(at).max - 1
    _step(at).set_value(last)
    at.run()
    assert any("Die Zielmenge 61 ist erreicht" in c for c in _captions(at))


def test_play_runs_through_all_frames_without_duplicate_chart_keys():
    """Beim Abspielen entstehen in einem Lauf mehrere Diagramme mit demselben Namen - die Schlüssel tragen deshalb den Schritt."""
    at = _run(lambda a: a.session_state.__setitem__("net_select", "diamond"))
    [b for b in at.button if b.label == "▶️ Abspielen"][0].click()
    at.run()
    assert not at.exception, [e.value for e in at.exception]


def test_permalink_parameters_are_clamped_and_snapped():
    at = AppTest.from_file(str(APP), default_timeout=600)
    at.query_params["density"] = "9999"
    at.query_params["spread"] = "abc"
    at.query_params["p"] = "-5"
    at.query_params["target"] = "5"
    at.run()
    assert not at.exception
    assert at.slider(key="density_slider").value == C.DENSITY_MAX and at.slider(key="spread_slider").value == C.DEFAULT_SPREAD and at.slider(key="p_slider").value == C.P_MIN
    assert at.slider(key="target_slider").value == C.TARGET_MIN
    at = AppTest.from_file(str(APP), default_timeout=600)
    at.query_params["density"] = "63"
    at.query_params["spread"] = "60"
    at.query_params["load"] = "94"
    at.query_params["target"] = "83"
    at.run()
    assert at.slider(key="density_slider").value == 60 and at.slider(key="spread_slider").value == 50 and at.slider(key="load_slider").value == 90 and at.slider(key="target_slider").value == 80


def test_unknown_values_in_the_permalink_fall_back_to_the_defaults():
    at = AppTest.from_file(str(APP), default_timeout=600)
    at.query_params["net"] = "ring"
    at.query_params["search"] = "astar"
    at.run()
    assert not at.exception and at.selectbox(key="net_select").value == C.DEFAULT_NET and at.radio(key="search_radio").value == C.DEFAULT_SEARCH


def test_randomize_moves_the_seed_but_not_the_distribution():
    at = _run()
    pick = lambda a: ([m.value for m in a.metric if m.label == "Runden"][0], [m.value for m in a.metric if m.label == "Durchsuchte Kanten"][1], _metric(a, "Mehrkosten des kostenblinden Flusses"))
    before = pick(at)
    seed_before = at.number_input(key="seed_input").value
    [b for b in at.sidebar.button if "Neues Netz" in b.label][0].click()
    at.run()
    assert not at.exception and at.number_input(key="seed_input").value != seed_before and pick(at) == before


def test_experiments_run_on_demand():
    at = _run()
    assert not any("Mittel über 10 feste Netze je Größe" in c for c in _captions(at))
    assert not any("Mittel über 10 feste Netze." in c for c in _captions(at))
    for key in ("scaling_start", "capacity_start"):
        at.button(key=key).click()
        at.run()
        assert not at.exception, [e.value for e in at.exception]
    text = " ".join(_captions(at))
    assert "Mittel über 10 feste Netze je Größe" in text and "Die Zahl der Runden bleibt gleich" in text


def test_experiments_on_a_fixed_net_show_hints_instead_of_dead_controls():
    at = _run(lambda a: a.session_state.__setitem__("net_select", "diamond"))
    assert not [b for b in at.button if b.key in ("scaling_start", "capacity_start")]
    assert sum("zufälliges Distributionsnetz wählen" in t for t in _texts(at)) >= 5


def _calls(src, name):
    """Der Text jedes Aufrufs `name(...)` einschließlich verschachtelter Klammern."""
    out = []
    for m in re.finditer(re.escape(name) + r"\(", src):
        depth, i = 1, m.end()
        while depth:
            depth += {"(": 1, ")": -1}.get(src[i], 0)
            i += 1
        out.append(src[m.start():i])
    return out


def test_every_plotly_chart_has_an_explicit_key_and_axes_are_locked():
    calls = _calls(APP.read_text(encoding="utf-8"), "plotly_chart")
    assert len(calls) == 10 and all(re.search(r'key=f?"[a-z_]+(_\{\w+\})?"', c) for c in calls), calls
    assert len({re.search(r'key=f?"([a-z_]+?)(?:_\{\w+\})?"', c).group(1) for c in calls}) == 10            # jeder Schlüssel nur einmal
    viz = (ROOT / "ssp_visualization.py").read_text(encoding="utf-8")
    bodies = [b for b in viz.split(chr(10) + "def ") if b.startswith("build_")]
    assert "fixedrange=True" in viz and len(bodies) == 7 and all("_base(" in b or "_layout(" in b for b in bodies)


def test_app_text_has_no_links_to_repository_files():
    assert not re.search(r"\]\(\w+\.py\)", APP.read_text(encoding="utf-8"))


def test_footer_is_verbatim():
    src = APP.read_text(encoding="utf-8")
    assert "https://sebastianhanisch.net/kontakt.html" in src and "Interesse an einer maßgeschneiderten Lösung für" in src and "Operations Research und Machine Learning" in src


def test_runtime_needs_only_numpy_pandas_plotly_streamlit():
    """Konvention der Konzepte-Wurzeln und -Stücke: Referenzbibliotheken (scipy, networkx) nur als Testorakel."""
    req = (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
    assert "scipy" not in req and "networkx" not in req
    for path in ROOT.glob("*.py"):
        assert not re.search(r"^\s*(import|from)\s+(scipy|networkx)\b", path.read_text(encoding="utf-8"), re.M), path.name
