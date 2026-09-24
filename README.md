# Successive Shortest Paths – der billigste Fluss – Streamlit-Demo

*(noch nicht deployed)*

Viertes Stück der **Netzwerkfluss-Linie** der "Konzepte"-Reihe für die Website "Sebastian Hanisch – Operations Research und Machine Learning", Fortsetzung von [Edmonds-Karp](https://github.com/sebastian-hanisch/edmonds-karp-demo), [Dinic](https://github.com/sebastian-hanisch/dinic-demo) und [Push-Relabel](https://github.com/sebastian-hanisch/push-relabel-demo):
anders als die Fall-Demos im Portfolio (ein Anwendungsfall, mehrere Verfahren im Vergleich) zeigt diese Demo **ein** Verfahren – **Successive Shortest Paths** (SSP; Jewell 1958, Busacker und Gowen 1960, Iri 1960) – an einem wachsenden Beispiel.
Die drei Vorgänger finden den **größten** Fluss und ignorieren die Kosten. SSP füllt in jeder Runde den **billigsten** Weg von S nach T im Restgraphen auf (nicht den mit den wenigsten Kanten); eine Rückkante – ein zurückgenommener Fluss – kostet **minus** ihre Kosten.
Nach jeder Runde ist der Fluss ein **kostenminimaler Fluss seiner Menge**; die Preise der Wege steigen von Runde zu Runde, die Kostenkurve über der Menge ist konvex. **Potenziale** (Schattenpreise der Knoten) machen die Suche mit Dijkstra möglich und sind am Ende das Optimalitätszertifikat.
Vehikel wie in den Vorgänger-Demos: ein Distributionsnetz (Werke → Verteilzentren → Filialen) mit Kosten je Einheit, dazu zwei Lehrnetze.

**Einordnung in die Reihe (die Kanten des Graphen):** SSP setzt an der einen Schwäche an, die alle drei Vorgänger nennen: Kostenblindheit. Auf einem Netz mit Einheitskapazitäten zwischen Fahrzeugen und Aufträgen ist SSP die **Ungarische Methode** (Matching-Linie, `hungarian-demo`) – hier die allgemeine Fassung mit Kapazitäten.
Der umgekehrte Weg (zuerst irgendein zulässiger Fluss, dann negative Kreise löschen) ist **Cycle-Canceling** (gebaut: [cycle-canceling-demo](https://github.com/sebastian-hanisch/cycle-canceling-demo)); **Cost Scaling** (gebaut: [cost-scaling-demo](https://github.com/sebastian-hanisch/cost-scaling-demo)) ist Push-Relabel mit ε-optimalen Preisen. Bisher gebaut: die ersten elf Stücke.
```
edmonds-karp-demo (Wurzel: Restgraph, Rückkanten, Max-Flow = Min-Cut)                  [gebaut]
  ├─ dinic-demo (viele kürzeste Wege je Phase: Niveaugraph, blockierender Fluss)        [gebaut]
  ├─ push-relabel-demo (kein Weg: Überschüsse schieben, Höhen anheben)                 [gebaut]
  └─ ssp-demo (Kosten: der billigste Weg im Restgraphen, Potenziale)                    [dieses Stück]
       ├─ cycle-canceling-demo → Netzwerksimplex (network-flow-demo)                    [gebaut / gebaut als Fall-Demo]
       ├─ cost-scaling-demo (Push-Relabel + ε-Skalierung, das nutzt OR-Tools)           [gebaut]
       └─ multicommodity-demo (mehrere Güter teilen Kapazität: Kanten-LP, Preise)       [gebaut]
            ├─ mcf-column-generation-demo (Pfade als Spalten, Pricing = Dijkstra)       [gebaut]
            ├─ garg-koenemann-demo (Näherung mit Preisen, ohne LP-Löser)                [gebaut]
            └─ fixkosten-netzdesign-demo (Fixkosten: Schranke und Schnitte)             [gebaut]
                 ├─ benders-demo (Entwurf im Master, Fluss im Teilproblem)              [gebaut]
                 └─ Slope Scaling (Heuristik für große Netze)                           [geplant]
```

## Ergebnis (Zahlen aus den Tests)

Jede hier genannte Zahl ist in `tests/test_claims.py` belegt: die Lehrnetze von Hand, die Beispielnetze über ihre Seeds, die Verteilungen über 100 feste Netze (Seeds 100000–100099, dieselben wie in den Vorgänger-Demos). Standard: 3 Werke, 3 Verteilzentren, 8 Filialen, Netzdichte 60 %, Streuung 50 %, Auslastung 90 %, der größte Fluss, Dijkstra mit Potenzialen. Kosten je Einheit: Werk 1–5, Lane 1–9, Verteilzentrum 1–3, Filialnachfrage 0. Edmonds-Karp ist aus der Vorgänger-Demo kopiert; ein Test bewacht die Kopie (52 475 durchsuchte Kanten über die 100 Netze).

| Frage | Ergebnis |
|---|---|
| Ist der Fluss kostenminimal? | ✅ Ja, in allen 100 Netzen exakt gleich dem Optimum von `networkx` (`max_flow_min_cost`), auch mit Bellman-Ford als Suche; zusätzlich gegen ein lineares Programm (`scipy`, HiGHS), gegen `scipy.optimize.linear_sum_assignment` (Zuordnung: 10) und Brute-Force-Aufzählung (Raute: 10). Mit Zielmenge gegen `networkx.network_simplex` mit Bedarfen. |
| Ist jeder Zwischenfluss kostenminimal für seine Menge? | ✅ Nach jeder Runde aus dem Trace geprüft: Kosten = Optimum für genau diese Menge (`networkx`), Potenziale gültig (reduzierte Kosten aller Restkanten ≥ 0), Preis des Weges = Schattenpreis von T, Kosten der Runde = Preis × Engpass, die Kanten des Weges reduziert genau 0. Am Ende kein negativer Kreis im Restgraphen (unabhängig per `networkx`-Bellman-Ford). |
| Wie viel spart das gegen den kostenblinden Fluss? | ✅ Der Fluss von Edmonds-Karp (derselbe Wert) kostet im Mittel **12,7 % mehr** (Median 11,1 %, 90. Perzentil 24,3 %, höchstens 57 %); nur in 2 von 100 Netzen ist er zufällig billigst. Beispielnetz: 1339 gegen 1197 (+11,9 %); Zuordnung mit Kosten: 25 gegen 10. |
| Steigen die Wegpreise? | ✅ In 100 von 100 Netzen sind die Preise nicht fallend, die Kostenkurve ist konvex. Beispielnetz: von 11 für die erste bis 25 für die letzte Einheit, im Mittel 15,8. |
| Wie teuer ist die letzte Einheit? | ⚠️ Im Mittel das **1,6-fache** des Durchschnittspreises (Median 1,57, höchstens 2,35); das letzte Zehntel der Menge verursacht 15 % der Gesamtkosten statt 10 %. **80 % der Menge kosten im Beispielnetz nur 74 % des Gesamtpreises** (61 Einheiten für 883 statt 76 für 1197). |
| Wie oft nutzt der billigste Weg eine Rückkante? | ✅ Im Mittel in 2,7 von 11,6 Runden (höchstens 10); im Beispielnetz 3 von 14. Die Raute zeigt den Fall im Kleinen: erste Einheit S-A-B-T für 3, zweite S-B-A-T über die Rückkante B→A für 4 − 1 + 4 = 7; zusammen 10. |
| Braucht SSP mehr Runden als Edmonds-Karp? | ⚠️ Ein wenig: 11,6 gegen 11,1 im Mittel (höchstens 18); in 50 von 100 Netzen mehr, in 25 gleich viele, in 25 weniger. |
| Dijkstra mit Potenzialen oder Bellman-Ford? | ✅ Beide liefern dieselben Kosten; Dijkstra durchsucht **539** Kanten, Bellman-Ford **953** (das 1,8-fache), Dijkstra in 100 % der Netze höchstens so viele. Der Abstand wächst mit dem Netz: von 12 auf 166 Knoten das 1,49- bis 2,52-fache; Steigung im doppelt logarithmischen Diagramm 1,69 (Dijkstra) gegen 1,81 (Bellman-Ford). |
| Was passiert ohne Potenziale? | ❌ Dijkstra auf den echten Kosten (Rückkanten mit −c) liefert in **32 von 100 Netzen** einen teureren Fluss – dort im Mittel 1,1 % (höchstens 3,8 %), ohne Warnung. Beispielnetz mit Seed 170: 1420 statt 1382 (+2,7 %); der Beweis im letzten Bild schlägt fehl (kein gültiges Potenzial). Durchsuchte Kanten: 565, kaum mehr als mit Potenzialen. |
| Pseudopolynomial – in der Praxis? | ✅ Nein: Kapazitäten × 1, 10, 100, 1000 lassen die Runden bei 12,1 (10 Netze) und die Wegfolge in 100 % der Netze unverändert; Menge und Kosten wachsen mit dem Faktor. Die Schranke „Runden ≤ Flusswert“ ist weit entfernt. |
| Wie oft wird die gesamte Nachfrage geliefert? | ⚠️ In 20 von 100 Netzen; sonst deckt das Netz nur einen Teil (Beispiel „Werke knapp“: 89 von 118). SSP liefert dann die billigsten 89. |

## Was nicht funktioniert hat / Vorab-Hypothesen

Vor dem Schreiben der Texte wurde über die 100 Netze gemessen; einige Vermutungen aus dem Plan stimmten nicht oder nur teilweise:

- **„Die letzte Einheit ist um ein Vielfaches teurer als der Durchschnitt.“** Abgeschwächt: im Mittel das 1,6-fache, höchstens das 2,4-fache. Die Kostenkurve ist konvex, aber nicht dramatisch.
- **„SSP braucht deutlich mehr Runden als Edmonds-Karp, weil der billigste Weg nicht der kürzeste ist.“** Kaum: 11,6 gegen 11,1. Der Unterschied liegt im Preis, nicht in der Zahl der Wege.
- **„Der naive Dijkstra auf echten Kosten scheitert selten.“** Das Gegenteil: er scheitert in fast jedem dritten Netz, nur meist um wenige Prozent. Deshalb ist der Fehler tückisch – es gibt keine Fehlermeldung, nur einen etwas schlechteren Fluss.
- **„Dijkstra mit Potenzialen ist bei diesen kleinen Netzen kaum besser als Bellman-Ford.“** Doch, deutlich: schon beim kleinsten Netz (12 Knoten) das 1,5-fache an durchsuchten Kanten, beim größten (166 Knoten) das 2,5-fache.
- **Zielmenge ohne Neuberechnung:** SSP kennt zu jedem Zeitpunkt den billigsten Fluss der bisherigen Menge – ein Fluss der Zielmenge ist dieselbe Wegfolge, nur der letzte Weg wird gekürzt (Regler „Zielmenge“).
- **Fallstrick beim Potenzial-Update (im Test nachgestellt):** der Zuwachs muss min(d(v), d(T)) sein. Die Suche bricht bei T ab, die Entfernungen dahinter sind nur vorläufig; wer sie trotzdem als Zuwachs nimmt, bekommt in 39 von 40 geprüften Netzen ungültige Potenziale (reduzierte Kosten < 0 auf einer Restkante). Der Test „Potenziale gültig nach jeder Runde“ schlägt dann an.
- **Abweichungen vom Plan:** Port 8674 statt 8673 (von der parallel gebauten Myerson-Satterthwaite-Demo belegt); keine Zeit-Erweiterung; kein PDF-Export.

## Was die Demo zeigt

- **Runden in Aktion:** Schritt-Slider und ▶️ über die Bilder: **Start** (der leere Fluss), je **Runde** ein Bild (der billigste Weg grün mit Menge × Kosten je Einheit, Rückkanten orange gestrichelt, Knotenfarbe = Schattenpreis π), am Schluss der fertige Fluss mit dem **Beweis**. Rechts die **Grenzkosten** (ein Balken je Runde: Breite = Menge, Höhe = Preis, die Fläche ist der Gesamtpreis) und die **Kostenkurve** (Gesamtkosten über der Menge, Steigung = Preis). Im Endbild: reduzierte Kosten aller Restkanten ≥ 0, komplementärer Schlupf, Vergleich mit dem Edmonds-Karp-Fluss.
- **Die Menge zum kleinsten Preis:** Menge, Gesamtkosten (gegen Edmonds-Karp), Preis der letzten Einheit, durchsuchte Kanten; Verteilung über 100 feste Netze. Der Regler „Zielmenge“ (20–100 % des größten Flusses) zeigt, was die letzten Einheiten kosten.
- **Experimente (🔬):** Kostenblindheit behoben (Histogramm der Mehrkosten), Preis der letzten Einheit, Dijkstra mit Potenzialen gegen Bellman-Ford (Verteilung und Skalierung von 12 bis 166 Knoten), ohne Potenziale, pseudopolynomial (Kapazitäten × 1000).
- **Feste Netze** (Raute mit Umleitung, Zuordnung mit Kosten) und zufällige Distributionsnetze; **Wo die Annahmen enden:** welches spätere Stück an welcher Schwäche ansetzt.

## Modell und Verfahren

- **Netz und Restgraph:** wie in den Vorgänger-Demos (Quelle S, Werke, Verteilzentren als Eingang und Ausgang gespalten, Filialen, Senke T; Restkanten als Paar 2i/2i+1), zusätzlich Kosten je Einheit c ≥ 0; die Rückkante hat Kosten −c. Ganzzahlig, eigener Zufallsgenerator SplitMix64 statt `numpy.random`.
- **SSP:** wiederhole: suche den billigsten S-T-Weg im Restgraphen, fülle ihn bis zum Engpass auf (mit Zielmenge: höchstens bis zur Zielmenge). Invariante: kein negativer Kreis im Restgraphen, also kostenminimal für die aktuelle Menge.
- **Potenziale:** π(v) mit reduzierten Kosten c + π(u) − π(v) ≥ 0 auf allen Restkanten; nach jeder Suche π(v) += min(d(v), d(T)). Dijkstra darf laufen, obwohl Rückkanten negative echte Kosten haben; π(T) − π(S) ist der Preis der zuletzt gelieferten Einheit.
- **Suchen:** Dijkstra mit Potenzialen (das Verfahren), Bellman-Ford mit Warteschlange (Referenz), Dijkstra ohne Potenziale (Negativkontrolle, kein zulässiges Verfahren).
- **Zertifikat:** für einen beliebigen Fluss Potenziale per Bellman-Ford von einem gedachten Start mit Kosten 0; sie sind genau dann gültig, wenn der Fluss kostenminimal für seine Menge ist.
- **Laufzeit:** O(F · (m + n log n)) mit Fibonacci-Halde – pseudopolynomial (F = Flusswert); gemessen als durchsuchte Kanten.

## Dateien

| Datei | Inhalt |
|---|---|
| `app.py` | Streamlit-Oberfläche |
| `ssp_constants.py` | Regler-Grenzen, Presets und Hilfetexte, feste Seed-Mengen |
| `ssp_presets.py` | Permalink, Preset- und Zufalls-Seed-Logik (Standardmuster des Portfolios) |
| `ssp_scenario.py` | Distributionsnetz mit Kosten, eigener Zufallsgenerator, Lehrnetze (Raute, Zuordnung mit Kosten), Kapazitäts-Skalierung |
| `ssp_algorithm.py` | Successive Shortest Paths mit drei Suchen, Zielmenge, Trace je Runde, Zertifikat |
| `ssp_edmonds_karp.py` | Kopie der Vorgänger-Demo als Vergleichsbasis (ohne Import, durch einen Test bewacht) |
| `ssp_evaluation.py` | Urteil, Verteilungen, Kostenkurve, Skalierung, Kapazitäts-Tabelle, Optimalitätsprüfung |
| `ssp_visualization.py` | Plotly-Abbildungen (Achsen gesperrt für Touch-Geräte; Hover über unsichtbare Marker entlang der Kanten) |
| `tests/` | Algorithmus (Handfälle, `networkx`/`scipy`/Brute Force als Gegenprobe, Invarianten je Runde, Zertifikat, Negativkontrolle, Kapazitäts-Skalierung), Szenario und Auswertung, Presets, belegte Zahlen, AppTest-Rauchtests |

Alle Daten sind synthetisch; die Laufzeit braucht nur numpy, pandas, plotly und streamlit (scipy und networkx sind reine Testorakel).

## Lokal starten

```bash
python -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\streamlit run app.py
```

## Tests ausführen

```bash
venv\Scripts\pip install -r requirements-dev.txt
venv\Scripts\python -m pytest tests -v
```

Die Logik rechnet ausschließlich mit ganzen Zahlen; die im Text genannten Anteile und Mediane sind deshalb auf jeder Plattform identisch.
Die CI (`.github/workflows/tests.yml`) läuft auf Ubuntu mit Python 3.12, bei jedem Push und wöchentlich mit den jeweils neuesten Bibliotheksversionen.
