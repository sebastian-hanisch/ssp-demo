"""Successive Shortest Paths - der billigste Fluss - interaktive Konzept-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Anders als die Fall-Demos im Portfolio (ein Anwendungsfall, mehrere Verfahren im Vergleich) zeigt diese Demo EIN Verfahren - Successive Shortest Paths mit Potenzialen (Schattenpreisen) - und lässt stattdessen das Beispiel wachsen.
Viertes Stück der Netzwerkfluss-Linie der "Konzepte"-Reihe: behebt die Kostenblindheit von "Edmonds-Karp", "Dinic" und "Push-Relabel". Siehe README für die Einordnung.

Lauffähig mit: streamlit run app.py
"""

import time

import streamlit as st

import ssp_algorithm as ssp
import ssp_constants as C
import ssp_evaluation as ev
import ssp_scenario as sc
from ssp_presets import (
    KEPT,
    apply_preset,
    bounds,
    init_session_state_defaults,
    load_permalink_settings,
    randomize_seed,
    seed_widget,
    sync_query_params,
)
from ssp_scenario import build
from ssp_visualization import (
    build_cost_curve,
    build_network,
    build_price_bars,
    build_ratio_hist,
    build_scaling,
    build_search_compare,
    build_surcharge_hist,
)

st.set_page_config(page_title="Successive Shortest Paths – Sebastian Hanisch", layout="wide")

SEARCH_SHORT = {"dijkstra": "Dijkstra mit Potenzialen", "spfa": "Bellman-Ford", "naive": "Dijkstra ohne Potenziale"}


def _pct(x, digits=1):
    return "–" if x is None else f"{x:.{digits}f} %".replace(".", ",")


def _share(x):
    """Anteil (0..1) als 'nn %'."""
    return f"{100 * x:.0f} %"


def _f(x, digits=1):
    return "–" if x is None else f"{x:.{digits}f}".replace(".", ",")


def _int(x):
    return f"{int(round(x)):,}".replace(",", " ")


def _stage_text(stage_caps):
    parts = [f"{sc.KIND_LABELS[k]} {v}" for k, v in stage_caps.items() if k in ev.STAGE_KINDS]
    return ", ".join(parts)


@st.cache_resource(show_spinner=False, max_entries=32)
def _analysis(params, search, target):
    return ev.analyse(build(*params), search, target)


st.title("💶 Successive Shortest Paths – der billigste Fluss")
st.markdown(
    """
Edmonds-Karp, Dinic und Push-Relabel finden den **größten** Fluss - was er kostet, ist ihnen gleich. In den Netzen dieser Demo ist ihr Fluss im Mittel 12,7 % teurer als der billigste Fluss derselben Menge.
**Successive Shortest Paths** (SSP) wählt in jeder Runde nicht den kürzesten, sondern den **billigsten** Weg von S nach T im Restgraphen und füllt ihn auf. Eine Rückkante (ein zurückgenommener Fluss) kostet dabei **minus** ihre Kosten - wer Fluss zurücknimmt, spart Geld.
Das Ergebnis nach jeder Runde ist ein **kostenminimaler Fluss seiner Menge**; die Preise der Wege steigen von Runde zu Runde, die Kostenkurve über der Menge ist **konvex** - die letzte Einheit ist die teuerste.
Diese Demo zeigt Runde für Runde, was das im Netz bedeutet, wie **Potenziale** (Schattenpreise der Knoten) die Suche beschleunigen und die Optimalität beweisen - und was passiert, wenn man sie weglässt.
"""
)
st.caption(
    "Anders als die Fall-Demos im Portfolio, die an einem Anwendungsfall mehrere Verfahren vergleichen, zeigt diese Demo - viertes Stück der Netzwerkfluss-Linie der \"Konzepte\"-Reihe, Fortsetzung von \"Edmonds-Karp\", \"Dinic\" und \"Push-Relabel\" - **ein** Verfahren an einem wachsenden Beispiel. "
    "Auf einem Netz mit Einheitskapazitäten zwischen Fahrzeugen und Aufträgen ist SSP die **Ungarische Methode** (Zuordnung mit Kosten: Demo \"Hungarian\" der Matching-Linie). Der umgekehrte Weg - zuerst irgendein zulässiger Fluss, dann negative Kreise löschen - ist **Cycle-Canceling** (gebaut)."
)

with st.expander("So funktioniert Successive Shortest Paths", expanded=True):
    st.markdown(
        r"""
1. **Start:** der leere Fluss. Er ist kostenminimal für die Menge 0.
2. **Restgraph:** jede Kante mit freier Kapazität ist eine **Vorwärtskante** mit Kosten $c$; jede Kante mit Fluss hat eine **Rückkante** mit Kosten $-c$ (Fluss zurücknehmen spart Geld).
3. **Billigster Weg:** finde den Weg von S nach T im Restgraphen mit den kleinsten Gesamtkosten je Einheit - nicht mit den wenigsten Kanten. Fülle ihn bis zum Engpass auf. Der Preis dieser Einheiten steht in der Runde fest.
4. **Warum das genügt:** ein Fluss ist genau dann kostenminimal für seine Menge, wenn der Restgraph **keinen Kreis mit negativen Kosten** hat. Ein billigster Weg erzeugt keinen; also bleibt jeder Zwischenfluss kostenminimal - bis kein Weg mehr existiert.
5. **Potenziale:** jeder Knoten bekommt einen Schattenpreis $\pi(v)$. Mit den **reduzierten Kosten** $c+\pi(u)-\pi(v)\ge 0$ läuft die Suche mit Dijkstra statt mit Bellman-Ford. Nach jeder Suche steigt $\pi(v)$ um die gefundene Entfernung (höchstens die von T) - die Potenziale bleiben gültig und sind am Ende das **Optimalitätszertifikat**.
6. **Rückkanten:** die zweite Einheit im Beispiel „Raute“ muss eine Kante zurücknehmen - der billigste Weg kann eine Rückkante nutzen, deren Kosten negativ sind. Ohne Potenziale (Dijkstra auf den echten Kosten) geht das schief.
        """
    )

st.caption("🎯 Schnellstart – ein Beispielnetz laden:")
names = list(C.PRESETS.keys())
for row in range(0, len(names), 4):
    preset_cols = st.columns(4)
    for col, name in zip(preset_cols, names[row:row + 4]):
        with col:
            st.button(name, width="stretch", on_click=apply_preset, args=(name,), help=C.PRESET_HELP[name])

st.caption(
    "🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, "
    "um ein Szenario zu teilen."
)

load_permalink_settings()
init_session_state_defaults()

with st.sidebar:
    st.header("⚙️ Einstellungen")
    net_key = st.selectbox(
        "Netz", list(C.NETS), key="net_select", format_func=lambda k: C.NETS[k],
        help="Ein zufälliges Distributionsnetz mit Kosten je Einheit, oder eines der festen Lehrnetze: die Raute (eine Rückkante mit Kosten −1) und die Zuordnung mit Kosten (SSP = Ungarische Methode).",
    )
    search = st.radio(
        "Suche nach dem billigsten Weg", list(C.SEARCH_LABELS), key="search_radio", format_func=lambda k: C.SEARCH_LABELS[k],
        help="Dijkstra mit Potenzialen (reduzierte Kosten, alle ≥ 0) ist das Verfahren. Bellman-Ford findet dieselben Wege ohne Potenziale, aber mit mehr durchsuchten Kanten. Dijkstra auf den echten Kosten ist die Negativkontrolle: es hält einen Knoten für fertig, den eine Rückkante noch verbilligen könnte.",
    )
    target = st.slider("Zielmenge [% des maximalen Flusses]", *bounds("target_slider"), key="target_slider", step=10,
                       help="Wie viel geliefert werden soll. Bei weniger als 100 % wird der letzte Weg gekürzt - SSP liefert die billigste Menge dieser Größe. Die teuersten Einheiten kommen zuletzt: 80 % der Menge kosten im Standardnetz nur 74 % des Gesamtpreises.")
    if net_key == "random":
        seed_widget("p_slider")
        p = st.slider("Werke", *bounds("p_slider"), key="p_slider", help="Anzahl der Werke (oben im Netz); Kosten je Einheit 1 bis 5.")
        st.session_state[KEPT["p_slider"]] = p
        seed_widget("d_slider")
        d = st.slider("Verteilzentren", *bounds("d_slider"), key="d_slider", help="Anzahl der Verteilzentren; Umschlagkosten 1 bis 3 je Einheit, Durchsatz 30 bis 60 % der gesamten Werkskapazität.")
        st.session_state[KEPT["d_slider"]] = d
        seed_widget("s_slider")
        s = st.slider("Filialen", *bounds("s_slider"), key="s_slider", help="Anzahl der Filialen (unten im Netz).")
        st.session_state[KEPT["s_slider"]] = s
        seed_widget("density_slider")
        density = st.slider("Netzdichte [%]", *bounds("density_slider"), key="density_slider", step=10, help="Anteil der möglichen Lanes (Werk → Verteilzentrum, Verteilzentrum → Filiale), die es gibt; Kosten je Lane 1 bis 9.")
        st.session_state[KEPT["density_slider"]] = density
        seed_widget("spread_slider")
        spread = st.slider("Streuung der Lane-Breiten [%]", *bounds("spread_slider"), key="spread_slider", step=25, help="0 = alle Lanes einer Stufe gleich breit, 100 = Kapazitäten gleichverteilt von 1 bis zum Doppelten der Grundbreite.")
        st.session_state[KEPT["spread_slider"]] = spread
        seed_widget("load_slider")
        load = st.slider("Auslastung [% der Werkskapazität]", *bounds("load_slider"), key="load_slider", step=10, help="Gesamtnachfrage der Filialen in Prozent der gesamten Werkskapazität. Über 100 % kann das Netz die Nachfrage nicht mehr decken.")
        st.session_state[KEPT["load_slider"]] = load
        seed_widget("seed_input")
        seed = st.number_input("Zufalls-Seed", *bounds("seed_input"), key="seed_input", step=1)
        st.session_state[KEPT["seed_input"]] = seed
        st.button("🎲 Neues Netz generieren", width="stretch", on_click=randomize_seed, help="Würfelt einen neuen Zufalls-Seed. Die Verteilungen über 100 feste Netze weiter unten ändern sich dabei nicht - nur die Marke „Ihre Ziehung“ wandert.")
    else:
        p = int(st.session_state.get(KEPT["p_slider"], C.DEFAULT_P))
        d = int(st.session_state.get(KEPT["d_slider"], C.DEFAULT_D))
        s = int(st.session_state.get(KEPT["s_slider"], C.DEFAULT_S))
        density = int(st.session_state.get(KEPT["density_slider"], C.DEFAULT_DENSITY))
        spread = int(st.session_state.get(KEPT["spread_slider"], C.DEFAULT_SPREAD))
        load = int(st.session_state.get(KEPT["load_slider"], C.DEFAULT_LOAD))
        seed = int(st.session_state.get(KEPT["seed_input"], C.DEFAULT_SEED))
        st.caption("Dieses Netz ist fest - es gibt nichts zu erzeugen. Zahl der Werke, Verteilzentren und Filialen, Netzdichte, Streuung, Auslastung und Seed gehören zum zufälligen Netz.")

sync_query_params({"net_select": net_key, "search_radio": search, "target_slider": int(target), "p_slider": int(p), "d_slider": int(d), "s_slider": int(s),
                   "density_slider": int(density), "spread_slider": int(spread), "load_slider": int(load), "seed_input": int(seed)})

# feste Netze ignorieren die Zufallsregler: sonst würden gleiche Netze unter verschiedenen Schlüsseln mehrfach berechnet
params = (net_key, int(p), int(d), int(s), int(density), int(spread), int(load), int(seed))
if net_key in C.FIXED_NETS:
    params = (net_key, C.DEFAULT_P, C.DEFAULT_D, C.DEFAULT_S, C.DEFAULT_DENSITY, C.DEFAULT_SPREAD, C.DEFAULT_LOAD, C.DEFAULT_SEED)
with st.spinner("Rechne..."):
    a = _analysis(params, search, int(target))
net, res = a.net, a.result
level, code, dat = ev.verdict(a)
settings = (int(p), int(d), int(s), int(density), int(spread), int(load))
rounds = res.rounds
n_frames = len(rounds) + 2                       # Bild 0 = leerer Fluss, dann eine Runde je Bild, zuletzt der Beweis
is_fixed = net_key in C.FIXED_NETS

# --- Runden in Aktion --------------------------------------------------------------------------------------------------------------------------

st.markdown("## 🎯 Runden in Aktion")
owner = (params, search, int(target))
if st.session_state.get("ssp_step_owner") != owner:
    st.session_state["ssp_step"] = n_frames - 1
    st.session_state["ssp_step_owner"] = owner
step_col, play_col = st.columns([5, 2])
with step_col:
    step = st.slider("Bild", 0, n_frames - 1, key="ssp_step", help="Bild 0 ist der leere Fluss; jedes weitere Bild ist eine Runde (ein billigster Weg wird aufgefüllt); ganz rechts der fertige Fluss und der Optimalitätsbeweis.")
with play_col:
    auto_play = st.button("▶️ Abspielen", width="stretch")
view_slot = st.empty()

zero_flow = tuple(0 for _ in net.arcs)
final_pi = res.potentials if search == "dijkstra" else None
if search != "dijkstra":
    cert_pi, cert_ok = ssp.certificate(net, res.flow)
    final_pi = tuple(x - cert_pi[net.s] for x in cert_pi) if cert_ok else None
proof_data = ev.proof(net, res.flow, final_pi) if final_pi is not None else None


def _path_text(rnd):
    return " → ".join(net.names[v] for v in rnd.nodes)


def _render(k):
    """Bild k: links das Netz mit dem billigsten Weg der Runde und den Schattenpreisen, rechts Grenzkosten und Kostenkurve; am Ende der Beweis."""
    with view_slot.container():
        c1, c2 = st.columns(2)
        if k >= len(rounds) + 1:
            c1.markdown(f"**Fertiger Fluss** - Menge {res.value}, Gesamtkosten {res.total}")
            c1.plotly_chart(build_network(net, res.flow, pi=final_pi), width="stretch", key=f"result_map_{k}")
            c2.markdown("**Beweis:** Potenziale und Kostenkurve")
            c2.plotly_chart(build_price_bars(rounds, len(rounds)), width="stretch", key=f"proof_bars_{k}")
            c2.plotly_chart(build_cost_curve(rounds, len(rounds), ek_point=(a.edmonds_karp.value, a.ek_cost) if a.target is None else None), width="stretch", key=f"proof_curve_{k}")
            if final_pi is None:
                st.caption(f"**Kein gültiges Potenzial:** der Restgraph enthält einen Kreis mit negativen Kosten - der Fluss (Gesamtkosten {res.total}) ist nicht kostenminimal, der billigste Fluss dieser Menge kostet {dat['optimal_total']}. "
                           "Der Fluss ließe sich billiger machen, indem man Fluss um diesen Kreis herumschiebt (das ist die Idee von Cycle-Canceling).")
            else:
                base = (f"Die Schattenpreise π (Knotenfarbe) beweisen die Optimalität: für **alle {proof_data['checked']} Restkanten** sind die reduzierten Kosten c + π(u) − π(v) ≥ 0 (Vorwärtsrest) bzw. ≤ 0 (Kante mit Fluss); "
                        f"{proof_data['tight']} der {proof_data['flow_arcs']} Flusskanten haben reduzierte Kosten genau 0 (jede nicht volle gehört dazu), die übrigen sind voll. Damit gibt es keinen negativen Kreis im Restgraphen: **kein Fluss dieser Menge ist billiger**. π(T) − π(S) = {final_pi[net.t] - final_pi[net.s]} ist der Preis der zuletzt gelieferten Einheit.")
                if a.target is None:
                    base += (f" Der Fluss von Edmonds-Karp (rotes Kreuz) hat dieselbe Menge und kostet {a.ek_cost}" + (f" - {_pct(dat['ek_gap_pct'])} mehr." if dat["ek_gap_pct"] else " - hier ist er zufällig genauso billig."))
                st.caption(base)
            return
        if k == 0:
            c1.markdown("**Start:** der leere Fluss")
            c2.markdown("**Grenzkosten und Kostenkurve** - noch nichts geliefert")
            flow_k, pi_k, path_k = zero_flow, (tuple(0 for _ in range(net.n)) if search == "dijkstra" else None), None
            cap = "Der leere Fluss ist kostenminimal für die Menge 0. Alle Potenziale sind 0 (alle Kosten sind ≥ 0). Jede Runde füllt den billigsten Weg auf." if search == "dijkstra" else "Der leere Fluss ist kostenminimal für die Menge 0."
        else:
            r = rounds[k - 1]
            flow_k = r.flow_after
            pi_k = r.potentials if search == "dijkstra" else None
            path_k = [(e // 2, e % 2 == 0, r.bottleneck) for e in r.path]
            c1.markdown(f"**Runde {k}:** {r.bottleneck} Einheiten zu je {r.price}")
            c2.markdown(f"**Grenzkosten und Kostenkurve** - Menge {r.value}, Gesamtkosten {r.total}")
            cap = f"Billigster Weg: {_path_text(r)} - {r.length} Kanten, {r.price} je Einheit, Engpass {r.bottleneck}, durchsucht wurden {r.scanned} Kanten."
            if r.uses_back_arc:
                cap += " Der Weg nimmt **Fluss über eine Rückkante zurück** (orange, gestrichelt): das spart die Kosten dieser Kante."
            if search == "dijkstra":
                cap += f" Der Schattenpreis von T ist jetzt {r.price} - so viel kostet die zuletzt gelieferte Einheit, keine spätere ist billiger."
            if a.target is not None and k == len(rounds) and r.value == a.target:
                cap += f" Die Zielmenge {a.target} ist erreicht, der letzte Weg wurde gekürzt."
        c1.plotly_chart(build_network(net, flow_k, pi=pi_k, path=path_k), width="stretch", key=f"path_map_{k}")
        c2.plotly_chart(build_price_bars(rounds, k), width="stretch", key=f"price_bars_{k}")
        c2.plotly_chart(build_cost_curve(rounds, k), width="stretch", key=f"cost_curve_{k}")
        st.caption(cap)


if auto_play:
    for k in range(n_frames):
        _render(k)
        time.sleep(min(0.6, 8.0 / max(n_frames, 1)))
    step = n_frames - 1
else:
    _render(step)

st.caption("Links: Breite ~ Fluss (dunkelblau = Kante voll), Knotenfarbe = Schattenpreis π; grün = die Kanten des billigsten Weges dieser Runde (+Menge × Kosten je Einheit), orange gestrichelt = Rückkante (nimmt Fluss zurück, Kosten negativ). "
           "Rechts oben: Balken = Runden, Breite = Menge, Höhe = Preis je Einheit (die Fläche ist der Gesamtpreis); rechts unten: Gesamtkosten über der Menge, Steigung = Preis - sie knickt nach oben, weil jede Runde teurer ist als die davor.")

st.markdown("---")

# --- Kernfrage: die Menge zum kleinsten Preis ---------------------------------------------------------------------------------------------------

st.markdown("## 🎯 Die Menge zum kleinsten Preis")
st.caption("**Runden** = wie oft ein Weg aufgefüllt wird; **Preis der letzten Einheit** = Grenzkosten der zuletzt gelieferten Einheit; **durchsuchte Kanten** = Aufwand (jede in einer Adjazenzliste angesehene Restkante, auch in der letzten, gescheiterten Suche), nie Sekunden.")
m1, m2, m3, m4 = st.columns(4)
if net.logistic:
    m1.metric("Menge", f"{dat['value']}" + (f" von {dat['demand']}" if a.target is None else f" (Ziel {a.target})"), delta=f"{_pct(dat['share'])} der Nachfrage" if a.target is None else f"{_pct(100 * dat['value'] / dat['max_value'], 0)} des möglichen Flusses", delta_color="off",
              help="Gelieferte Menge; bei einer Zielmenge unter 100 % nur ein Teil des größten Flusses.")
else:
    m1.metric("Menge", f"{dat['value']}", help="Menge von S nach T.")
if a.target is None and dat["ek_total"]:
    m2.metric("Gesamtkosten", f"{dat['total']}", delta=f"Edmonds-Karp: {dat['ek_total']}" + (f" (+{_pct(dat['ek_gap_pct'])})" if dat["ek_gap_pct"] else ""), delta_color="off",
              help="Kosten des Flusses. Edmonds-Karp liefert dieselbe Menge, wählt aber den Weg mit den wenigsten Kanten und ignoriert die Kosten.")
else:
    m2.metric("Gesamtkosten", f"{dat['total']}", delta=f"⌀ {_f(dat['avg_price'], 1)} je Einheit", delta_color="off", help="Bei einer Zielmenge unter 100 % gibt es keinen Vergleichsfluss von Edmonds-Karp (er liefert immer den größten Fluss).")
m3.metric("Preis der letzten Einheit", f"{dat['last_price']}", delta=f"erste Einheit {dat['first_price']}, ⌀ {_f(dat['avg_price'], 1)}", delta_color="off", help="Grenzkosten der zuletzt gelieferten Einheit; die erste war die billigste. Die Preise der Wege steigen von Runde zu Runde.")
m4.metric("Durchsuchte Kanten", f"{dat['scanned']}", delta=f"{dat['rounds']} Runden, {dat['back_rounds']} über Rückkanten", delta_color="off", help=f"Edmonds-Karp braucht auf demselben Netz {dat['ek_rounds']} Wege.")

if code == "optimal":
    served = ""
    if net.logistic and a.target is None:
        served = " Die gesamte Nachfrage wird geliefert." if dat["value"] == dat["demand"] else f" Das Netz schafft höchstens {dat['value']} von {dat['demand']} Einheiten ({_f(dat['share'], 0)} %); Engpass: **{_stage_text(dat['stage_caps'])}**."
    if a.target is None:
        cmp = (f" Der kostenblinde Fluss von Edmonds-Karp wäre {_pct(dat['ek_gap_pct'])} teurer ({dat['ek_total']})." if dat["ek_gap_pct"] else " Der Fluss von Edmonds-Karp ist hier zufällig genauso billig.")
    else:
        cmp = f" Ein Fluss der Menge {dat['value']} kostet mindestens {dat['total']} - billiger geht es nicht."
    st.success(f"✅ Kostenminimal: Menge {dat['value']} kostet {dat['total']} ({_f(dat['avg_price'], 1)} je Einheit, von {dat['first_price']} für die erste bis {dat['last_price']} für die letzte).{served}{cmp}")
elif code == "wrong":
    st.warning(f"⚠️ **Nicht kostenminimal:** {SEARCH_SHORT[search]} liefert Menge {dat['value']} für {dat['total']}, der billigste Fluss dieser Menge kostet {dat['optimal_total']} - der Fluss ist {_pct(dat['gap_pct'])} teurer als nötig. "
               "Ein einmal abgeschlossener Knoten wird nie mehr verbessert; mit Rückkanten (negative Kosten) kann ein späterer Weg ihn aber noch verbilligen.")
else:
    st.warning("⚠️ Es kommt gar nichts an: kein Weg führt von einem Werk über ein Verteilzentrum zu einer Filiale. Die Menge ist 0, die erste Suche scheitert sofort.")

if is_fixed:
    st.info("Festes Netz: es gibt nur diese eine Ziehung. Für die Verteilungen über viele Netze ein zufälliges Distributionsnetz wählen.")
    dist = None
else:
    dist = ev.distribution(*settings)
    st.markdown(f"**Nicht nur dieses eine Netz:** {len(C.DIST_SEEDS)} feste Netze mit denselben Einstellungen (Werke {p}, Verteilzentren {d}, Filialen {s}, Netzdichte {density} %, Streuung {spread} %, Auslastung {load} %), getrennt vom Seed oben; jeweils der größte Fluss.")
    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Runden", _f(dist["rounds_mean"], 1), delta=f"Edmonds-Karp {_f(dist['ek_rounds_mean'], 1)}, höchstens {dist['rounds_max']}", delta_color="off", help="Wege je Netz im Mittel: SSP und Edmonds-Karp brauchen ähnlich viele, SSP nur andere.")
    p2.metric("Preis der letzten Einheit", _f(dist["last_price_mean"], 1), delta=f"⌀ {_f(dist['avg_price_mean'], 1)} je Einheit", delta_color="off", help="Mittel über die Netze: Grenzkosten der letzten gegen den Durchschnitt aller Einheiten.")
    p3.metric("Über Rückkanten", _f(dist["back_rounds_mean"], 1), delta=f"höchstens {dist['back_rounds_max']}", delta_color="off", help="Runden, deren billigster Weg Fluss zurücknimmt, je Netz.")
    p4.metric("Durchsuchte Kanten", _f(dist["dijkstra_mean"], 0), delta=f"Bellman-Ford {_f(dist['spfa_mean'], 0)}", delta_color="off", help="Mittel über die Netze: Dijkstra mit Potenzialen gegen Bellman-Ford.")

st.markdown("---")

# --- Vergleich -----------------------------------------------------------------------------------------------------------------------------

with st.expander("🔧 Wie wir das erreichen – die Suchen im Vergleich"):
    st.markdown("**Was jede Suche für das Netz oben findet**")
    rows = []
    for name in ssp.SEARCHES:
        r = ssp.ssp(net, name, a.target, keep_trace=False)
        rows.append((SEARCH_SHORT[name], r.value, r.total, len(r.rounds), r.scanned_total, "ja" if r.total == a.optimum.total else f"nein (+{_pct(ev.pct(r.total - a.optimum.total, a.optimum.total))})"))
    st.table({"Suche": [r[0] for r in rows], "Menge": [r[1] for r in rows], "Gesamtkosten": [r[2] for r in rows], "Runden": [r[3] for r in rows], "durchsuchte Kanten": [r[4] for r in rows], "kostenminimal": [r[5] for r in rows]})
    st.caption("Dijkstra mit Potenzialen und Bellman-Ford liefern dieselben Kosten (die Wege dürfen sich bei Gleichständen unterscheiden), unterscheiden sich aber im Aufwand. Dijkstra ohne Potenziale ist nur eine Negativkontrolle.")
    st.markdown("**Protokoll der Runden** (aktuelle Einstellung)")
    if rounds:
        st.dataframe({"Runde": list(range(1, len(rounds) + 1)), "Weg": [_path_text(r) for r in rounds], "Menge": [r.bottleneck for r in rounds], "Preis je Einheit": [r.price for r in rounds],
                      "Rückkante": ["ja" if r.uses_back_arc else "" for r in rounds], "Gesamtmenge": [r.value for r in rounds], "Gesamtkosten": [r.total for r in rounds], "durchsuchte Kanten": [r.scanned for r in rounds]},
                     hide_index=True, width="stretch")
    else:
        st.caption("Keine Runde.")

st.markdown("---")

# --- Experimente -------------------------------------------------------------------------------------------------------------------------

st.subheader("🔬 Kostenblindheit behoben")
st.caption("Edmonds-Karp, Dinic und Push-Relabel liefern den größten Fluss, ohne auf die Kosten zu schauen. SSP liefert die gleiche Menge zum kleinsten Preis. Wie viel teurer ist der kostenblinde Fluss?")
if dist is None:
    st.info("Für die Verteilung über viele Netze ein zufälliges Distributionsnetz wählen. Für das feste Netz oben zeigt die Kennzahl „Gesamtkosten“ den Vergleich.")
else:
    e1, e2, e3, e4 = st.columns(4)
    e1.metric("Mehrkosten des kostenblinden Flusses", _pct(dist["ek_gap_mean"]), delta=f"Median {_pct(dist['ek_gap_median'])}", delta_color="off", help="Mittel über die Netze: Kosten des Edmonds-Karp-Flusses gegen den billigsten Fluss derselben Menge, in % des billigsten.")
    e2.metric("90. Perzentil", _pct(dist["ek_gap_p90"]), delta=f"höchstens {_pct(dist['ek_gap_max'])}", delta_color="off", help="In 10 % der Netze sind die Mehrkosten größer als dieser Wert.")
    e3.metric("Zufällig schon billigst", _share(dist["share_ek_optimal"]), help="Anteil der Netze, in denen der Edmonds-Karp-Fluss zufällig genauso billig ist.")
    e4.metric("Alle Nachfrage geliefert", _share(dist["share_all_served"]), help="Anteil der Netze, in denen der größte Fluss die gesamte Nachfrage deckt.")
    st.plotly_chart(build_surcharge_hist(dist["cols"]["ek_gap"], current=dat["ek_gap_pct"] if (net.logistic and a.target is None) else None), width="stretch", key="surcharge_chart")
    st.caption(f"Über {len(C.DIST_SEEDS)} feste Netze: der kostenblinde Fluss kostet im Mittel {_pct(dist['ek_gap_mean'])} mehr, im Median {_pct(dist['ek_gap_median'])}; nur in {_share(dist['share_ek_optimal'])} der Netze ist er zufällig billigst. "
               "SSP ist dagegen nach Konstruktion optimal - die Tests vergleichen seine Kosten mit dem Optimum von `networkx` und mit einem linearen Programm.")

st.subheader("🔬 Preis der letzten Einheit")
st.caption("Die Preise der Wege steigen von Runde zu Runde: eine Runde ist nie billiger als die vorige. Die Kostenkurve über der Menge ist deshalb konvex, und die letzte Einheit ist die teuerste.")
if dist is None:
    st.info("Für die Verteilung über viele Netze ein zufälliges Distributionsnetz wählen. Für das feste Netz oben zeigen die Grenzkosten-Balken die Preise je Runde.")
else:
    f1, f2, f3, f4 = st.columns(4)
    f1.metric("Preise nicht fallend", _share(dist["share_monotone"]), help="Anteil der Netze, in denen kein Weg billiger ist als der vorige.")
    f2.metric("Letzte ÷ ⌀ Einheit", _f(dist["ratio_last_mean"], 2), delta=f"Median {_f(dist['ratio_last_median'], 2)}, höchstens {_f(dist['ratio_last_max'], 2)}", delta_color="off", help="Preis der letzten Einheit im Verhältnis zum Durchschnittspreis, Mittel über die Netze.")
    f3.metric("Kosten der letzten 10 % der Menge", _share(dist["share_last10_mean"]), help="Anteil der Gesamtkosten, den das letzte Zehntel der Menge verursacht (Mittel über die Netze). Bei gleichem Preis je Einheit wären es 10 %.")
    f4.metric("Über Rückkanten", _f(dist["back_rounds_mean"], 1), delta=f"von {_f(dist['rounds_mean'], 1)} Runden", delta_color="off", help="Runden je Netz, deren billigster Weg Fluss zurücknimmt.")
    st.plotly_chart(build_ratio_hist(dist["cols"]["ratio_last"], current=(dat["last_price"] / dat["avg_price"]) if (net.logistic and a.target is None and dat["avg_price"]) else None), width="stretch", key="ratio_chart")
    st.caption(f"Über {len(C.DIST_SEEDS)} feste Netze: die letzte Einheit kostet im Mittel das {_f(dist['ratio_last_mean'], 2)}-fache des Durchschnittspreises (höchstens das {_f(dist['ratio_last_max'], 2)}-fache) - kein Faktor von mehreren Größenordnungen, aber deutlich. "
               f"Das letzte Zehntel der Menge verursacht {_share(dist['share_last10_mean'])} der Gesamtkosten statt 10 %. Wer 100 % liefern will, zahlt für die letzten Einheiten viel - der Zielmengen-Regler zeigt das.")

st.subheader("🔬 Dijkstra mit Potenzialen gegen Bellman-Ford")
st.caption("Beide finden den billigsten Weg, auch mit Rückkanten. Mit den Potenzialen sind alle reduzierten Kosten nicht negativ, Dijkstra darf einen Knoten abschließen und muss ihn nie mehr anfassen. Bellman-Ford braucht das nicht, sucht aber mehrfach über dieselben Kanten.")
if dist is None:
    st.info("Für die Verteilung über viele Netze ein zufälliges Distributionsnetz wählen. Für das feste Netz oben zeigt der Vergleich im Expander die durchsuchten Kanten.")
else:
    ratio = dist["spfa_mean"] / dist["dijkstra_mean"]
    st.plotly_chart(build_search_compare(dist["cols"]["dijkstra"], dist["cols"]["spfa"], dist["cols"]["naive"], current=dat["scanned"] if (net.logistic and search == "dijkstra") else None), width="stretch", key="search_chart")
    st.table({"Suche": ["Dijkstra mit Potenzialen", "Bellman-Ford", "Dijkstra ohne Potenziale"], "durchsuchte Kanten (Mittel)": [_f(dist["dijkstra_mean"], 0), _f(dist["spfa_mean"], 0), _f(dist["naive_mean"], 0)],
              "durchsuchte Kanten (Median)": [_f(dist["dijkstra_median"], 0), _f(dist["spfa_median"], 0), _f(dist["naive_median"], 0)], "größter Wert": [dist["dijkstra_max"], dist["spfa_max"], dist["naive_max"]]})
    st.caption(f"Über {len(C.DIST_SEEDS)} feste Netze: Bellman-Ford durchsucht im Mittel das {_f(ratio, 2)}-fache der Kanten von Dijkstra mit Potenzialen; Dijkstra ist in {_share(dist['share_dijkstra_le_spfa'])} der Netze höchstens so aufwendig. "
               "Beide liefern in jedem Netz dieselben Gesamtkosten (die Wege dürfen sich bei Gleichständen unterscheiden).")
    if st.button("Netze von 12 bis 166 Knoten durchrechnen (dauert einige Sekunden)", key="scaling_start"):
        st.session_state["scaling_on"] = True
    if st.session_state.get("scaling_on"):
        with st.spinner("Rechne 6 Netzgrößen × 10 Netze × 2 Suchen..."):
            sc_rows = ev.scaling()
        slopes = ev.slopes(sc_rows)
        st.plotly_chart(build_scaling(sc_rows), width="stretch", key="scaling_chart")
        st.table({"Werke / DCs / Filialen": [f"{r['size'][0]} / {r['size'][1]} / {r['size'][2]}" for r in sc_rows], "Knoten": [_f(r["n"], 0) for r in sc_rows], "Kanten": [_f(r["m"], 0) for r in sc_rows], "Runden": [_f(r["rounds"], 1) for r in sc_rows],
                  "Dijkstra mit Potenzialen": [_int(r["dijkstra"]) for r in sc_rows], "Bellman-Ford": [_int(r["spfa"]) for r in sc_rows], "Bellman-Ford ÷ Dijkstra": [_f(r["spfa"] / r["dijkstra"], 2) for r in sc_rows]})
        st.caption(f"Mittel über 10 feste Netze je Größe (Netzdichte 60 %, Streuung und Auslastung auf den Standardwerten). Steigung im doppelt logarithmischen Diagramm: Dijkstra mit Potenzialen {_f(slopes['dijkstra'], 2)}, Bellman-Ford {_f(slopes['spfa'], 2)} - beide wachsen etwas schneller als die Kantenzahl, weil mit dem Netz auch die Zahl der Runden wächst. "
                   f"Bellman-Ford liegt in jeder Größe darüber ({_f(min(r['spfa'] / r['dijkstra'] for r in sc_rows), 2)}- bis {_f(max(r['spfa'] / r['dijkstra'] for r in sc_rows), 2)}-fach).")

st.subheader("🔬 Ohne Potenziale: wenn Dijkstra irrt")
st.caption("Dijkstra auf den echten Kosten hält einen Knoten für fertig, sobald er drankommt. Mit Rückkanten (negative Kosten) kann ein später gefundener Weg ihn aber noch verbilligen - der frühere Abschluss war dann falsch. Wie oft passiert das?")
if dist is None:
    st.info("Für die Verteilung über viele Netze ein zufälliges Distributionsnetz wählen. Für das feste Netz oben zeigt der Vergleich im Expander, ob „Dijkstra ohne Potenziale“ hier kostenminimal ist.")
else:
    wrong_gaps = [g for g in dist["cols"]["naive_gap"] if g > 0]
    g1, g2, g3 = st.columns(3)
    g1.metric("Netze mit falschem Ergebnis", _share(dist["share_naive_wrong"]), help="Anteil der Netze, in denen Dijkstra ohne Potenziale einen teureren Fluss als den billigsten liefert.")
    g2.metric("Mehrkosten dort (Mittel)", _pct(sum(wrong_gaps) / len(wrong_gaps) if wrong_gaps else 0.0), delta=f"höchstens {_pct(max(wrong_gaps) if wrong_gaps else 0.0)}", delta_color="off", help="Nur die Netze, in denen es falsch ist.")
    g3.metric("Runden über Rückkanten", _f(dist["back_rounds_mean"], 1), help="Je Netz im Mittel; nur dann kann der Fehler überhaupt entstehen.")
    st.caption(f"Über {len(C.DIST_SEEDS)} feste Netze liefert Dijkstra ohne Potenziale in {_share(dist['share_naive_wrong'])} einen teureren Fluss - meist nur um wenige Prozent, aber ohne jede Warnung: es gibt keinen Fehler, nur ein schlechteres Ergebnis. Das Preset „Ohne Potenziale“ zeigt einen Fall; im Bild ganz rechts schlägt der Beweis fehl.")

st.subheader("🔬 Pseudopolynomial – und in der Praxis?")
st.caption("SSP braucht höchstens so viele Runden wie der Flusswert (jede Runde füllt mindestens eine Einheit): die Laufzeit hängt von den Zahlen ab, nicht nur von der Netzgröße. Kapazitäten × 1000 machen den Flusswert 1000-mal größer - die Runden?")
if is_fixed:
    st.info("Für dieses Experiment ein zufälliges Distributionsnetz wählen.")
else:
    if st.button("Kapazitäten mit 1, 10, 100 und 1000 multiplizieren (10 Netze)", key="capacity_start"):
        st.session_state["capacity_on"] = settings
    if st.session_state.get("capacity_on") == settings:
        cap_rows = ev.capacity_table(*settings)
        st.table({"Kapazitäten ×": [str(r["k"]) for r in cap_rows], "Runden (Mittel)": [_f(r["rounds"], 1) for r in cap_rows], "Flusswert (Mittel)": [_int(r["value"]) for r in cap_rows], "Gesamtkosten (Mittel)": [_int(r["total"]) for r in cap_rows],
                  "dieselbe Wegfolge": [_share(r["share_same"]) for r in cap_rows]})
        st.caption("Mittel über 10 feste Netze. Die Zahl der Runden bleibt gleich: jeder billigste Weg wird bis zum Engpass aufgefüllt, und alle Engpässe wachsen mit - die Wege und ihre Reihenfolge bleiben dieselben, Menge und Gesamtkosten wachsen mit dem Faktor. "
                   "Die Schranke „Runden ≤ Flusswert“ ist auch in diesen Netzen weit entfernt; sie ist ein Worst-Case-Satz. Konstruierte Netze, in denen jede Runde nur eine Einheit füllt, gibt es - hier kommen sie nicht vor.")

st.markdown("---")

# --- Grenzen -----------------------------------------------------------------------------------------------------------------------------

st.subheader("🚧 Wo die Annahmen enden")
st.markdown(
    """
| Annahme | Was passiert, wenn sie verletzt ist | Wer setzt an |
|---|---|---|
| **Alle Kosten sind nicht negativ** | Mit negativen Kosten sind die Startpotenziale 0 nicht gültig; man braucht einmal Bellman-Ford am Anfang. Hier gibt es nur Kosten ≥ 0 - nur Rückkanten sind negativ. | Nicht Thema dieser Demo |
| **Jede Runde ist kostenminimal für ihre Menge** | Das ist die Stärke: SSP hält Optimalität und baut die Zulässigkeit (die gewünschte Menge) Schritt für Schritt auf. Man kann das auch umgekehrt tun: zuerst irgendein zulässiger Fluss, dann negative Kreise löschen. | **Cycle-Canceling** (Stück 5, gebaut) |
| **Die Laufzeit hängt an der Menge** | SSP braucht höchstens so viele Runden wie der Flusswert (**pseudopolynomial**): bei Kapazitäten in Millionen kann es sehr viele Runden geben. Hier bleibt die Rundenzahl von der Größe der Kapazitäten unberührt. | **Cost Scaling** (Push-Relabel mit ε-optimalen Preisen, gebaut), **Netzwerksimplex** (Demo „network-flow-demo“) |
| **Ein Gut, teilbar** | Alle Waren sind gleich und beliebig teilbar. Mehrere Güter auf gemeinsamen Kanten machen den Fluss im Allgemeinen gebrochen. | **Mehrgüterfluss** (gebaut: multicommodity-demo) |
| **Keine Zeit** | Ein Fluss ist eine Momentaufnahme; Wartezeiten und Fahrpläne fehlen. | Zeit-Raum-Netz in der Demo „leercontainer-demo“ |
"""
)
st.caption("Die Netzwerkfluss-Linie ist als Ganzes geplant: Edmonds-Karp, Dinic, Push-Relabel, Successive Shortest Paths (dieses Stück), Cycle-Canceling (gebaut), Cost Scaling (gebaut), Mehrgüterfluss (gebaut), Column Generation (gebaut), Garg-Könemann (gebaut), Fixkosten-Netzwerkdesign, Benders-Zerlegung und Slope Scaling - bisher sind die ersten neun gebaut.")

st.markdown("---")

with st.expander("📐 Mathematische Formulierung"):
    st.markdown(
        r"""
**Modell (Min-Cost-Flow).** Gerichteter Graph $G=(V,E)$ mit Quelle $s$, Senke $t$, ganzzahligen Kapazitäten $u_e$ und Kosten $c_e\ge 0$ je Einheit. Gesucht ist ein Fluss $f$ der Menge $F$ mit minimalen Kosten:
$$\min\ \sum_e c_e f_e\quad\text{u.d.N.}\quad 0\le f_e\le u_e,\ \ \text{Flusserhaltung},\ \ \text{Wert}(f)=F.$$

**Restgraph.** Zu jeder Kante $e=(u,v)$ gibt es die Vorwärtskante $(u,v)$ mit Rest $u_e-f_e$ und Kosten $c_e$ und die Rückkante $(v,u)$ mit Rest $f_e$ und Kosten $-c_e$.

**Satz (kein negativer Kreis).** Ein Fluss $f$ ist kostenminimal unter allen Flüssen seines Wertes genau dann, wenn $G_f$ keinen Kreis mit negativen Gesamtkosten enthält.

**Potenziale.** Eine Funktion $\pi:V\to\mathbb Z$ mit **reduzierten Kosten** $c^\pi(u,v)=c(u,v)+\pi(u)-\pi(v)\ge 0$ für jede Restkante zeigt, dass es keinen negativen Kreis gibt (die $\pi$ heben sich auf jedem Kreis auf). Umgekehrt gibt es bei gültigem Fluss solche $\pi$: die Entfernungen im Restgraphen. Es sind die **Duallösungen** (Schattenpreise) der Flusserhaltung; $\pi(t)-\pi(s)$ ist der Preis der letzten Einheit.
**Komplementärer Schlupf:** $0<f_e<u_e\Rightarrow c^\pi_e=0$; $f_e=0\Rightarrow c^\pi_e\ge 0$; $f_e=u_e\Rightarrow c^\pi_e\le 0$.

**SSP-Invariante.** Nach jeder Runde ist $f$ kostenminimal für den Wert $F_k$. Beweis: der billigste Weg $P$ hat Kosten $d(t)$ im Restgraphen; das Auffüllen erzeugt nur Rückkanten von Kanten von $P$ mit Kosten $-c^\pi=0$ - sie sind reduziert 0, also entsteht kein negativer Kreis.

**Johnson-Update.** Nach der Suche mit reduzierten Kosten wird $\pi(v)\leftarrow\pi(v)+\min(d(v),d(t))$ gesetzt. Damit bleiben alle Restkanten reduziert $\ge 0$ und die Kanten des gefundenen Weges reduziert genau 0 - Dijkstra darf in jeder Runde laufen, obwohl die Rückkanten negative echte Kosten haben. Die Preise der Wege $\pi(t)-\pi(s)$ sind nicht fallend, die Kostenkurve $F\mapsto\text{Kosten}(F)$ ist konvex und stückweise linear.

**Laufzeit.** Jede Runde füllt mindestens eine Einheit: höchstens $F$ Runden. Mit Dijkstra und Fibonacci-Halde je Runde $O(m+n\log n)$: **$O(F\,(m+n\log n))$** - pseudopolynomial, denn $F$ hängt an den Kapazitäten. Bellman-Ford je Runde: $O(nm)$.

**Zuordnung.** Auf einem bipartiten Netz mit Einheitskapazitäten sind die Wege abwechselnde Wege des Matchings; SSP ist die **Ungarische Methode** (ihre Zeilen- und Spaltenpotenziale sind die Schattenpreise π).

Implementiert in `ssp_scenario.py` (Netze, eigener Zufallsgenerator), `ssp_algorithm.py` (billigste Wege mit Potenzialen, Bellman-Ford, die Negativkontrolle, Zertifikat), `ssp_edmonds_karp.py` (Kopie der Vorgänger-Demo als Vergleichsbasis), `ssp_evaluation.py` (Kennzahlen, Verteilungen, Experimente).
        """
    )

st.markdown("---")

st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning. Interesse an einer maßgeschneiderten Lösung für "
    "Ihr Unternehmen? [Kontakt aufnehmen](https://sebastianhanisch.net/kontakt.html)"
)
