# Arbeitsregeln für Claude in diesem Repo (topo-daten, Spurpläne D. Eckenstein)

1. **Regeln stehen nur in `spurplan/REGELN.md`** – an ihrer Stelle der Hierarchie (Ebenen 0–7), nie als datierter Abschnitt
   unten, nie in einer neuen md-Datei, nie nur in der Übergabe. Ein neuer Entscheid von Daniel ändert die passende Zeile oder
   fügt eine Zeile in der passenden Tabelle ein (Feld «alt»/«seit» mit Datum). Widersprüche → Abschnitt 7.
2. Übergabe-Nachträge (`spurplan/UEBERGABE.md` Abschnitt 6) verweisen auf die Regelnummer («REGELN 1.15»), statt die Regel
   auszuschreiben. `IDEEN_REVIEW.md` ist nur Backlog; was entschieden ist, wandert nach REGELN.md.
3. Neuer cfg-Schalter im Code → im selben Commit die Regel in REGELN.md nennen (Spalte «Code»). Ein Schalter gilt für **alle**
   Wege (Entscheid 13.11.: alle Bahnhöfe gleich); nur-Linien-Regionen-Schalter sind Altlast (Schritt V2).
4. Vor jedem Push: `python3 spurplan/code/regeln_lint.py` muss ohne Fehler laufen (Workflow `regeln` prüft es auch).
5. Arbeitsweise und Fahrplan: `spurplan/UEBERGABE.md` Abschnitt 0 und der eigene Schritt in Abschnitt 5 – nur diese lesen.
   Zuerst die Zugriffe holen (Repo mit Schreibrecht, Feedback-Seite/Datenbank), solange Daniel da ist. Nie abnehmen.
