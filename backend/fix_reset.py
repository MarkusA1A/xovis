#!/usr/bin/env python3
"""
Einmaliges Fix-Script: Erzwingt einen sauberen Tages-Reset der Live-Werte
und bereinigt falsche Einträge in der counts-Tabelle.

Verwendung im Docker-Container:
  docker exec xovis-dashboard python /app/backend/fix_reset.py
"""

import asyncio
import os
from datetime import datetime

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

        # 2. Falsche counts-Einträge von heute anzeigen und löschen
        today = datetime.now().strftime("%Y-%m-%d")

        async with db.execute("""
            SELECT COUNT(*) as cnt,
                   COALESCE(MAX(count_in), 0) as max_in,
                   COALESCE(MAX(count_out), 0) as max_out
            FROM counts WHERE date(timestamp) = ?
        """, (today,)) as cursor:
            counts_row = await cursor.fetchone()

        print(f"=== Counts-Tabelle für heute ({today}) ===")
        print(f"  Einträge:   {counts_row['cnt']}")
        print(f"  Max IN:     {counts_row['max_in']}")
        print(f"  Max OUT:    {counts_row['max_out']}")

        if counts_row['cnt'] > 0:
            await db.execute(
                "DELETE FROM counts WHERE date(timestamp) = ?", (today,)
            )
            print(f"  -> {counts_row['cnt']} falsche Einträge gelöscht")
        print()

        # 3. Live-Tabelle: base aktualisieren, counter auf 0
        old_base_in = row['base_in'] or 0
        old_base_out = row['base_out'] or 0
        old_count_in = row['count_in'] or 0
        old_count_out = row['count_out'] or 0

        new_base_in = old_base_in + old_count_in
        new_base_out = old_base_out + old_count_out

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

        # 4. Ergebnis anzeigen
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
        print("Reset erfolgreich! Zähler stehen auf 0.")
        print("Der nächste Sensor-Webhook liefert korrekte Tageswerte.")


if __name__ == "__main__":
    asyncio.run(fix_reset())
