# 🏃 Running Analytics Dashboard

Persönliche Trainingsanalyse auf Basis von Garmin-Daten — mit Fokus auf Marathon-Vorbereitung.

## Features

- **Trainingsvolumen** — wöchentliche und monatliche Kilometer
- **80/20-Regel** — Verteilung locker vs. intensiv (Herzfrequenz-basiert)
- **Konsistenz-Kalender** — GitHub-Style Heatmap deiner Lauftage
- **10%-Regel** — Wochenvolumen-Steigerung mit Verletzungsrisiko-Warnung
- **Aerobe Effizienz** — Pace-Trend bei lockeren Läufen über Zeit
- **Erholungsanalyse** — Ruhetage-Verteilung zwischen Läufen

## Eigene Daten verwenden

### Garmin Connect Export

1. Öffne [Garmin Connect](https://connect.garmin.com/) im Browser
2. Gehe zu **Aktivitäten** → **Alle Aktivitäten**
3. Filtere nach **Laufen** (optional)
4. Klicke oben rechts auf **Exportieren** → **CSV**
5. Speichere die Datei als `Activities.csv` im Ordner `data/`

### Datenformat

Die CSV muss folgende Spalten enthalten (Standard Garmin Export, Sprache: Deutsch):

| Spalte | Beschreibung |
|--------|-------------|
| Datum | Zeitstempel der Aktivität |
| Distanz | Distanz in km |
| Zeit | Dauer (HH:MM:SS) |
| Ø Herzfrequenz | Durchschnittliche Herzfrequenz |
| Ø Pace | Durchschnittspace (M:SS) |
| Titel | Name der Aktivität |

Weitere Spalten (Schrittfrequenz, Bodenkontaktzeit, Leistung etc.) werden genutzt, sind aber nicht zwingend erforderlich.

## Setup

```bash
cd dashboards/running_analytics
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Tech Stack

- **Python 3.12**
- **Streamlit** — Web-Dashboard
- **Plotly** — interaktive Charts
- **pandas** — Datenverarbeitung

## Screenshot

*Dashboard startet unter http://localhost:8501*
