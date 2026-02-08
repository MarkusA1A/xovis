#!/usr/bin/env python3
"""
Einmaliges Fix-Script: Erzwingt einen sauberen Tages-Reset der Live-Werte.

Verwendung im Docker-Container:
  docker exec xovis-dashboard python /app/backend/fix_reset.py
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta

import aiosqlite

DATABASE_PATH = os.getenv("DATABASE_PATH", "/data/xovis_counts.db")


async def fix_reset():
    print(f"Datenbank: {DATABASE_PATH}")
    print(f"Aktuelle Zeit: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row

        # 1. Aktuelle Live-Werte anzeigen
        async with db.execute("SELECT * FROM live WHERE id = 1") as cursor:
            row = await cursor.fetchone()
            if not row:
                print("FEHLER: Keine Live-Daten gefunden!")
                return

        print("=== VORHER (Live-Tabelle) ===")
        print(f"  count_in:        {row['count_in']}")
        print(f"  count_out:       {row['count_out']}")
        print(f"  occupancy:       {row['occupancy']}")
        print(f"  base_in:         {row['base_in']}")
        print(f"  base_out:        {row['base_out']}")
        print(f"  last_reset_date: {row['last_reset_date']}")
        print(f"  last_update:     {row['last_update']}")
        print()

        # 2. Reset erzwingen: base aktualisieren, counter auf 0
        old_base_in = row['base_in'] or 0
        old_base_out = row['base_out'] or 0
        old_count_in = row['count_in'] or 0
        old_count_out = row['count_out'] or 0

        new_base_in = old_base_in + old_count_in
        new_base_out = old_base_out + old_count_out
        today = datetime.now().strftime("%Y-%m-%d")

        await db.execute("""
            UPDATE live SET
                count_in = 0,
                count_out = 0,
                occupancy = 0,
                base_in = ?,
                base_out = ?,
                last_reset_date = ?
            WHERE id = 1
        """, (new_base_in, new_base_out, today))
        await db.commit()

        # 3. Ergebnis anzeigen
        async with db.execute("SELECT * FROM live WHERE id = 1") as cursor:
            row = await cursor.fetchone()

        print("=== NACHHER (Live-Tabelle) ===")
        print(f"  count_in:        {row['count_in']}")
        print(f"  count_out:       {row['count_out']}")
        print(f"  occupancy:       {row['occupancy']}")
        print(f"  base_in:         {row['base_in']}")
        print(f"  base_out:        {row['base_out']}")
        print(f"  last_reset_date: {row['last_reset_date']}")
        print()
        print("Reset erfolgreich! Die Zähler starten jetzt bei 0.")
        print("Der nächste Sensor-Webhook wird korrekte Tageswerte liefern.")


if __name__ == "__main__":
    asyncio.run(fix_reset())
