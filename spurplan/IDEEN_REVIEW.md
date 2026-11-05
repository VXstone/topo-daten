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

## Datenaufbereitung (Review topo-daten) – siehe UEBERGABE 5.11. spät
- R1 Release-Gate in vorbereitung.yml, R2 Geometrie in der Änderungssignatur (aenderungen.py). **Umgesetzt 5.11.2026:** betriebspunkte, gleisnummern, ausschnitte und release ohne continue-on-error (Fehler → kein Release, Vormonatsdatei bleibt, stand.json hält Teilfehler fest); sbb, perronkanten, aenderungen bleiben optional. Way-Signatur mit Geometrie auf 1e-5° gerundet. Wirkt ab dem nächsten Vorbereitungslauf.
