import aiosqlite
from datetime import datetime, timedelta
from config import DATABASE_PATH

async def init_db():
    """Initialisiert die Datenbank."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Historische Zählungen
        await db.execute("""
            CREATE TABLE IF NOT EXISTS counts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                count_in INTEGER DEFAULT 0,
                count_out INTEGER DEFAULT 0,
                occupancy INTEGER DEFAULT 0
            )
        """)
        await db.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON counts(timestamp)")

        # Live-Werte (nur eine Zeile)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS live (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                count_in INTEGER DEFAULT 0,
                count_out INTEGER DEFAULT 0,
                occupancy INTEGER DEFAULT 0,
                last_update DATETIME,
                last_reset_date TEXT
            )
        """)

        # Spalten hinzufügen falls sie fehlen (Migration für bestehende DBs)
        for column in [
            "last_reset_date TEXT",
            "base_in INTEGER DEFAULT 0",
            "base_out INTEGER DEFAULT 0",
        ]:
            try:
                await db.execute(f"ALTER TABLE live ADD COLUMN {column}")
            except Exception:
                pass  # Spalte existiert bereits

        # Initialen Live-Eintrag erstellen (mit last_reset_date für korrekten ersten Reset)
        await db.execute("""
            INSERT OR IGNORE INTO live (id, count_in, count_out, occupancy, last_reset_date)
            VALUES (1, 0, 0, 0, date('now', 'localtime'))
        """)

        await db.commit()


async def update_live_count(count_in: int, count_out: int, occupancy: int):
    """Aktualisiert die Live-Zählwerte."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            UPDATE live SET
                count_in = ?,
                count_out = ?,
                occupancy = ?,
                last_update = ?,
                last_reset_date = COALESCE(last_reset_date, date('now', 'localtime'))
            WHERE id = 1
        """, (count_in, count_out, occupancy, datetime.now().isoformat()))
        await db.commit()


async def check_daily_reset():
    """Prüft ob ein täglicher Reset nötig ist und führt ihn durch."""
    global _last_saved_values

    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM live WHERE id = 1") as cursor:
            row = await cursor.fetchone()
            if row:
                last_reset = row["last_reset_date"]
                today = datetime.now().strftime("%Y-%m-%d")

                if not last_reset or last_reset != today:
                    # Neuer Tag - Base-Offset für kumulative Sensorwerte aktualisieren
                    new_base_in = (row["base_in"] or 0) + (row["count_in"] or 0)
                    new_base_out = (row["base_out"] or 0) + (row["count_out"] or 0)

                    # Counter zurücksetzen, Base-Offset speichern
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

                    # In-Memory-Cache zurücksetzen
                    _last_saved_values = {"count_in": -1, "count_out": -1}
                    return True
    return False


async def get_live_count() -> dict:
    """Holt die aktuellen Live-Werte."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM live WHERE id = 1") as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return {"count_in": 0, "count_out": 0, "occupancy": 0, "last_update": None}


async def save_count(count_in: int, count_out: int, occupancy: int):
    """Speichert einen Zählwert in der Historie."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT INTO counts (count_in, count_out, occupancy) VALUES (?, ?, ?)",
            (count_in, count_out, occupancy)
        )
        await db.commit()


async def get_latest_count():
    """Holt den letzten gespeicherten Wert."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM counts ORDER BY timestamp DESC LIMIT 1"
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_hourly_stats(date: datetime):
    """Stündliche Statistiken für einen Tag."""
    start = date.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)

    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT
                strftime('%H', timestamp) as hour,
                MAX(count_in) as total_in,
                MAX(count_out) as total_out,
                MAX(occupancy) as max_occupancy
            FROM counts
            WHERE timestamp BETWEEN ? AND ?
            GROUP BY strftime('%H', timestamp)
            ORDER BY hour
        """, (start.isoformat(), end.isoformat())) as cursor:
            return [dict(row) for row in await cursor.fetchall()]


async def get_daily_stats(start_date: datetime, days: int = 7):
    """Tägliche Statistiken."""
    start = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=days)

    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT
                date(timestamp) as date,
                MAX(count_in) as total_in,
                MAX(count_out) as total_out,
                MAX(occupancy) as max_occupancy
            FROM counts
            WHERE timestamp BETWEEN ? AND ?
            GROUP BY date(timestamp)
            ORDER BY date
        """, (start.isoformat(), end.isoformat())) as cursor:
            return [dict(row) for row in await cursor.fetchall()]


async def get_monthly_stats(year: int, month: int):
    """Monatliche Statistiken."""
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)

    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT
                date(timestamp) as date,
                MAX(count_in) as total_in,
                MAX(count_out) as total_out,
                MAX(occupancy) as max_occupancy
            FROM counts
            WHERE timestamp BETWEEN ? AND ?
            GROUP BY date(timestamp)
            ORDER BY date
        """, (start.isoformat(), end.isoformat())) as cursor:
            return [dict(row) for row in await cursor.fetchall()]


# Letzter gespeicherter Wert (Cache um doppelte Einträge zu vermeiden)
_last_saved_values = {"count_in": -1, "count_out": -1}


async def save_count_if_changed(count_in: int, count_out: int, occupancy: int):
    """Speichert Werte nur wenn sie sich geändert haben."""
    global _last_saved_values

    # Nur speichern wenn sich die Werte geändert haben
    if count_in != _last_saved_values["count_in"] or count_out != _last_saved_values["count_out"]:
        await save_count(count_in, count_out, occupancy)
        _last_saved_values["count_in"] = count_in
        _last_saved_values["count_out"] = count_out
        return True
    return False
