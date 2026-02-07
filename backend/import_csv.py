"""Import historischer Xovis-Sensordaten aus CSV in die SQLite-Datenbank.

CSV-Format (Xovis Export, 1-Minuten-Intervalle):
    from-time,to-time,Forward counter,Backward counter
    31/01/2026 - 19:28,31/01/2026 - 19:29,0,0

Die Minutenwerte werden pro Stunde summiert und als kumulative
Tageswerte in die counts-Tabelle geschrieben (gleich wie der
Live-Webhook es tut).

Verwendung:
    python import_csv.py /pfad/zur/datei.csv
"""

import csv
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime

from config import DATABASE_PATH


def parse_timestamp(ts: str) -> datetime:
    """Parst Xovis-Timestamp 'DD/MM/YYYY - HH:MM'."""
    return datetime.strptime(ts.strip(), "%d/%m/%Y - %H:%M")


def import_csv(csv_path: str):
    # Minutendaten einlesen und pro Tag+Stunde summieren
    # Struktur: {date: {hour: {"fw": X, "bw": Y}}}
    daily_hourly = defaultdict(lambda: defaultdict(lambda: {"fw": 0, "bw": 0}))

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        row_count = 0
        for row in reader:
            fw = int(row["Forward counter"])
            bw = int(row["Backward counter"])
            if fw == 0 and bw == 0:
                continue

            dt = parse_timestamp(row["from-time"])
            date_str = dt.strftime("%Y-%m-%d")
            hour = dt.hour
            daily_hourly[date_str][hour]["fw"] += fw
            daily_hourly[date_str][hour]["bw"] += bw
            row_count += 1

    print(f"CSV gelesen: {row_count} Zeilen mit Daten")
    print(f"Tage mit Daten: {len(daily_hourly)}")

    # In DB schreiben
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Tabelle sicherstellen
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS counts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            count_in INTEGER DEFAULT 0,
            count_out INTEGER DEFAULT 0,
            occupancy INTEGER DEFAULT 0
        )
    """)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_timestamp ON counts(timestamp)"
    )

    inserted = 0
    skipped = 0

    for date_str in sorted(daily_hourly.keys()):
        hours = daily_hourly[date_str]
        cumulative_in = 0
        cumulative_out = 0

        for hour in sorted(hours.keys()):
            cumulative_in += hours[hour]["fw"]
            cumulative_out += hours[hour]["bw"]
            occupancy = max(0, cumulative_in - cumulative_out)

            # Timestamp: Mitte der Stunde
            ts = f"{date_str} {hour:02d}:30:00"

            # Prüfen ob bereits Daten für diese Stunde existieren
            cursor.execute(
                "SELECT id FROM counts WHERE timestamp BETWEEN ? AND ?",
                (f"{date_str} {hour:02d}:00:00", f"{date_str} {hour:02d}:59:59")
            )
            if cursor.fetchone():
                skipped += 1
                continue

            cursor.execute(
                "INSERT INTO counts (timestamp, count_in, count_out, occupancy) "
                "VALUES (?, ?, ?, ?)",
                (ts, cumulative_in, cumulative_out, occupancy)
            )
            inserted += 1

        # Tages-Zusammenfassung
        print(
            f"  {date_str}: IN={cumulative_in}, OUT={cumulative_out}, "
            f"Belegung={max(0, cumulative_in - cumulative_out)}"
        )

    conn.commit()
    conn.close()

    print(f"\nImport abgeschlossen: {inserted} Stunden eingefügt, {skipped} übersprungen (bereits vorhanden)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Verwendung: python import_csv.py <csv-datei>")
        sys.exit(1)

    csv_path = sys.argv[1]
    print(f"Importiere: {csv_path}")
    print(f"Datenbank: {DATABASE_PATH}")
    print()
    import_csv(csv_path)
