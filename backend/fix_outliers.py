"""Entfernt Ausreißer-Einträge aus der counts-Tabelle.

Die Ausreißer auf Sa. 7. Feb und So. 8. Feb entstanden beim Übergang
von CSV-Import zu Live-Webhook, weil der absolute Sensorwert statt
des tagesbezogenen Werts gespeichert wurde.
"""
import sqlite3
import os

DB_PATH = os.environ.get("DATABASE_PATH", "/app/data/xovis.db")
# Normaler Tageswert liegt bei ~400-600, alles über 800 ist ein Ausreißer
THRESHOLD = 800


def fix_outliers():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Vorher: Daten für die betroffenen Tage anzeigen
    print("=== Vor der Korrektur ===")
    for date in ["2026-02-07", "2026-02-08"]:
        c.execute("""
            SELECT MAX(count_in) as max_in, MAX(count_out) as max_out,
                   COUNT(*) as rows
            FROM counts WHERE date(timestamp) = ?
        """, (date,))
        row = c.fetchone()
        print(f"  {date}: {row['rows']} Einträge, MAX IN={row['max_in']}, MAX OUT={row['max_out']}")

    # Ausreißer-Einträge löschen
    c.execute("""
        DELETE FROM counts
        WHERE date(timestamp) IN ('2026-02-07', '2026-02-08')
          AND (count_in > ? OR count_out > ?)
    """, (THRESHOLD, THRESHOLD))
    deleted = c.rowcount
    conn.commit()
    print(f"\n{deleted} Ausreißer-Einträge gelöscht (Schwellwert: {THRESHOLD})")

    # Nachher: verbleibende Daten anzeigen
    print("\n=== Nach der Korrektur ===")
    for date in ["2026-02-07", "2026-02-08"]:
        c.execute("""
            SELECT MAX(count_in) as max_in, MAX(count_out) as max_out,
                   COUNT(*) as rows
            FROM counts WHERE date(timestamp) = ?
        """, (date,))
        row = c.fetchone()
        print(f"  {date}: {row['rows']} Einträge, MAX IN={row['max_in']}, MAX OUT={row['max_out']}")

    conn.close()


if __name__ == "__main__":
    fix_outliers()
