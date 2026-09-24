"""Konstanten, Regler-Grenzen, Presets und feste Seed-Mengen der Demo "Successive Shortest Paths: der billigste Fluss"."""

# --- Regler (wie in den Vorgänger-Demos) ----------------------------------------------------------------------------------------
P_MIN, P_MAX, DEFAULT_P = 2, 6, 3            # Werke
D_MIN, D_MAX, DEFAULT_D = 2, 6, 3            # Verteilzentren
S_MIN, S_MAX, DEFAULT_S = 3, 12, 8           # Filialen
DENSITY_MIN, DENSITY_MAX, DEFAULT_DENSITY = 20, 100, 60   # Anteil vorhandener Lanes in ganzen Prozent, Schritt 10
SPREAD_MIN, SPREAD_MAX, DEFAULT_SPREAD = 0, 100, 50       # Streuung der Lane-Breiten in ganzen Prozent, Schritt 25
LOAD_MIN, LOAD_MAX, DEFAULT_LOAD = 40, 160, 90            # Gesamtnachfrage in Prozent der Werkskapazität, Schritt 10
DEFAULT_SEED = 155
SEED_MAX = 2_000_000_000

NETS = {
    "random": "Zufälliges Distributionsnetz",
    "diamond": "Raute mit Umleitung (Rückkante mit Kosten −1)",
    "assignment": "Zuordnung mit Kosten (5 × 5, Ungarische Methode)",
}
DEFAULT_NET = "random"
FIXED_NETS = ("diamond", "assignment")

SEARCH_LABELS = {"dijkstra": "Dijkstra mit Potenzialen", "spfa": "Bellman-Ford (Warteschlange)", "naive": "Dijkstra ohne Potenziale (falsch bei Rückkanten)"}
DEFAULT_SEARCH = "dijkstra"
TARGET_MIN, TARGET_MAX, DEFAULT_TARGET = 20, 100, 100     # Zielmenge in Prozent des maximalen Flusses, Schritt 10

# --- feste Seed-Mengen (dieselben wie in der Edmonds-Karp-Demo; unabhängig vom Nutzer-Seed) -----------------------------------------
DIST_SEEDS = tuple(range(100000, 100100))
SWEEP_SEEDS = DIST_SEEDS[:40]
SCALE_SIZES = ((2, 2, 4), (3, 3, 8), (4, 4, 16), (6, 6, 32), (8, 8, 64), (12, 12, 128))   # (Werke, DCs, Filialen)
SCALE_SEEDS = DIST_SEEDS[:10]
CAPACITY_FACTORS = (1, 10, 100, 1000)

COLORS = {
    "flow": "#1f77b4", "path": "#2ca02c", "back": "#ff7f0e", "cut": "#d62728", "reach": "#2ca02c", "dead": "#9467bd",
    "unreach": "#8c8c8c", "faint": "rgba(150,150,150,0.45)", "node": "#111111", "optimal": "#d62728", "levels": "Viridis",
}

# --- Presets -----------------------------------------------------------------------------------------------------------------
_BASE = dict(net="random", search=DEFAULT_SEARCH, target=DEFAULT_TARGET, p=DEFAULT_P, d=DEFAULT_D, s=DEFAULT_S, density=DEFAULT_DENSITY, spread=DEFAULT_SPREAD, load=DEFAULT_LOAD, seed=DEFAULT_SEED)
PRESETS = {
    "🚚 Zufallsnetz": {**_BASE},
    "🐢 Bellman-Ford": {**_BASE, "search": "spfa"},
    "⚠️ Ohne Potenziale": {**_BASE, "search": "naive", "seed": 170},
    "🎯 80 % der Menge": {**_BASE, "target": 80},
    "🏭 Werke knapp": {**_BASE, "load": 140},
    "🕸️ Dünnes Netz": {**_BASE, "density": 30},
    "🔀 Raute mit Umleitung": {**_BASE, "net": "diamond"},
    "💑 Zuordnung mit Kosten": {**_BASE, "net": "assignment"},
}
PRESET_HELP = {
    "🚚 Zufallsnetz": "Das typische Distributionsnetz: die gesamte Nachfrage wird geliefert, drei der 14 Runden nehmen Fluss über eine Rückkante zurück. Der kostenblinde Flusswert (Edmonds-Karp) wäre 12 % teurer.",
    "🐢 Bellman-Ford": "Dasselbe Netz, aber die Suche nach dem billigsten Weg ohne Potenziale: dieselben Kosten, aber das 1,7-fache an durchsuchten Kanten (1376 statt 824).",
    "⚠️ Ohne Potenziale": "Dijkstra auf den echten Kosten, obwohl Rückkanten negativ kosten: ein abgeschlossener Knoten wird nie korrigiert - der Fluss wird 2,7 % teurer als nötig (und gleicht hier dem kostenblinden).",
    "🎯 80 % der Menge": "Nur 80 % des möglichen Flusses liefern: die billigsten Wege reichen, die teuren letzten Einheiten entfallen - 80 % der Menge kosten nur 74 % des Gesamtpreises.",
    "🏭 Werke knapp": "Nachfrage 140 % der Werkskapazität: das Netz schafft nur 89 von 118 Einheiten - SSP füllt trotzdem zuerst die billigsten Wege.",
    "🕸️ Dünnes Netz": "Nur 30 % der möglichen Lanes: weniger Auswahl, weniger Runden.",
    "🔀 Raute mit Umleitung": "Vier Knoten: die zweite Einheit kann nur S→B nehmen, muss dann A→B zurücknehmen (Rückkante mit Kosten −1) und über A→T laufen: 4 − 1 + 4 = 7. Summe 10.",
    "💑 Zuordnung mit Kosten": "5 Fahrzeuge, 5 Aufträge, Kosten 1 bis 9 - SSP auf diesem Netz ist die Ungarische Methode: Gesamtkosten 10, der kostenblinde Fluss käme auf 25.",
}
