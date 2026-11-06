# Ideen aus den Reviews (5.11.2026) – Arbeitsliste, noch nicht umgesetzt

Eigene Datei, damit sie nicht mit Übergaben anderer Chats kollidiert. Nach Umsetzung in REGELN.md überführen.

## Regel D. Eckenstein: Geografie ist leitgebend für die Reihenfolge, nicht für die Lage (5.11. 21:20)
- Was auf der Karte klar nördlich (östlich) liegt, darf im Plan nicht südlich (westlich) liegen (Tecknau nicht unterhalb Dulliken).
- Kein Vertauschen, nur weil am Nachbarknoten ein Abgang zu beiden Orten führt.
- Gleiche Höhe ist erlaubt, wenn nötig (Ins auf Höhe Lyss).
- Abstand und Winkel sind frei.
- Umsetzung: L2 mit Toleranz (gleiche Höhe kein Fehler; nur Paare mit deutlichem Kartenabstand, Grössenordnung km). L3 (Planachse > 60° neben Karte) nicht mehr als Strafe – gedrehte Achse ist ok, solange L2 nichts meldet. Danach MOB/Vereina neu messen (MOB-Frage Montbovon/Rochers de Naye/Chamby erledigt sich damit grösstenteils).

## Zeichenlogik (Review Gestaltung)
1. **Bahnhofsausfahrt als Ganzes:** gleichmässig auffächern, Gleisreihenfolge bleibt. Erste Testfälle: Selfranga (Versatz zu Selfranga Süd), Sagliains (Abgang Scuol, V an den Ladegleisen), Chamby (Knick 114). Bevorzugter nächster Schritt.
2. **Bündel als Einheit zeichnen:** parallele Gleise knicken gemeinsam (Treppen verhindern statt zählen).
3. **Kreuzung ohne Verbindung sichtbar:** kleine Unterbrechung im untergeordneten Gleis.
4. **Visuelle Hierarchie:** Nebengleise etwas dünner – Entscheid D. Eckenstein offen.
- Nicht übernommen: fester Winkelsatz 30/45/60° (widerspricht «Kippen ≤ 8° statt Versatz», Château-d'Oex).
- Schon vorhanden: Topologie vor Geometrie (T1–T6), Ruhe (T7), Bewertungsfunktion (Unruhe + lage_suche), Regression (Basis + Differenzbild), Pfeilverkettung (V/S).

## Standards / Blaupausen-Prüfstand (D. Eckenstein 6.11.2026) – Plan, Reihenfolge entschieden
- **Grundsatz:** parallel bleibt parallel im gleichen Abstand – gemessen quer zum Gleis, nicht senkrecht im Plan –, egal wie der Plan gedreht ist und unter welchem Winkel ein Gleis ihn verlässt. Standardisiert wird der Abstand, nicht der Winkel (kein fester Winkelsatz; Kippen ≤ 8° wie Château-d'Oex bleibt erlaubt).
- **Anlass:** h9o9 Sagliains. Im Plan Sagliains · Autoverlad verlassen zwei Nebengleise den Plan unter 60°, die Pfeile stehen senkrecht übereinander (13,2 px) → quer zur Schräge nur 6,6 px, im Regionalplan (Drehung −60°, Massstab 0,42) 2,7 px statt 10 px. Der connector gleicht die ~7 px je Gleis einzeln aus (T7 «leicht schräge Gerade») → ein Gleis läuft schräg.
- **Prüfstand:** jede Reinform/jeden Zusatz aus vorlage.py (Blaupause 2) in Drehungen 0, ±30, ±60, 90° und mit Abgängen gerade/30°/60° erzeugen; automatisch prüfen: Querabstand gleich, parallel bleibt parallel, Pfeile eines Bündels im Gleisabstand, Weichen gerundet, nichts unter 90°; zwei Blaupausen-Bahnhöfe gedreht nebeneinander verbinden → Verbindung gerade. Die Blaupause erzeugt nur die einfachen Bahnhöfe (Neuchâtel); geprüft werden die gemeinsamen Bausteine (Stummel, Pfeile, Ports, Rundungen, connector), die auch die OSM-Pläne (Vereina, MOB) benutzen.
- **Reihenfolge (je ein eigener Chat, nacheinander, nicht parallel – gleicher Code):**
  1. Prüfstand aufbauen (mit dem Sagliains-Fall als Baustein).
  2. Pfeile/Stummel bei schrägen Abgängen korrigieren → h9o9; Prüfstand zeigt weitere Stellen mit derselben Ursache.
  3. Bahnhofsausfahrt als Ganzes (Zeichenlogik 1): Selfranga / jxpf S-Kurve Klosters – Selfranga, Chamby.
  4. Bündel als Einheit (Zeichenlogik 2) im connector, als Schutz, wenn die Enden aus OSM-Gründen nicht passen.
  5. Montbovon +60° im Prüfstand nachstellen statt von Hand fixieren; danach Prüflauf über die abgenommenen SBB-Bahnhöfe (E9: Änderung zulässig bei gleicher Topologie, im Differenzbild).
- Perron-Standardlänge 80 px gehört als Standard in die Blaupause (Begutachtung Daniel).
- Unabhängig, Entscheid Daniel (kein eigener Chat nötig, Antwort auf der Feedbackseite): Montreux Gl. 4 (`gleisnummer_aus_ref` MOB), Weiche Caux, Kreuzung ohne Verbindung (Zeichenlogik 3), Nebengleise dünner (Zeichenlogik 4).

## Datenaufbereitung (Review topo-daten) – siehe UEBERGABE 5.11. spät
- R1 Release-Gate in vorbereitung.yml, R2 Geometrie in der Änderungssignatur (aenderungen.py). **Umgesetzt 5.11.2026:** betriebspunkte, gleisnummern, ausschnitte und release ohne continue-on-error (Fehler → kein Release, Vormonatsdatei bleibt, stand.json hält Teilfehler fest); sbb, perronkanten, aenderungen bleiben optional. Way-Signatur mit Geometrie auf 1e-5° gerundet. Wirkt ab dem nächsten Vorbereitungslauf.
