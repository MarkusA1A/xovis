import aiosqlite
from datetime import datetime, timedelta
from config import DATABASE_PATH

async def init_db():
    """Initialisiert die Datenbank und erstellt die Tabellen."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS counts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                count_in INTEGER DEFAULT 0,
                count_out INTEGER DEFAULT 0,
                current_occupancy INTEGER DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON counts(timestamp)
        """)
        await db.commit()

async def save_count(count_in: int, count_out: int, occupancy: int):
    """Speichert einen Zählwert in der Datenbank."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT INTO counts (count_in, count_out, current_occupancy) VALUES (?, ?, ?)",
            (count_in, count_out, occupancy)
        )
        await db.commit()

async def get_latest_count():
    """Holt den aktuellsten Zählwert."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM counts ORDER BY timestamp DESC LIMIT 1"
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def get_counts_range(start: datetime, end: datetime):
    """Holt Zählwerte für einen Zeitraum."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM counts WHERE timestamp BETWEEN ? AND ? ORDER BY timestamp",
            (start.isoformat(), end.isoformat())
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_hourly_stats(date: datetime):
    """Holt stündliche Statistiken für einen Tag."""
    start = date.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)

    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT
                strftime('%H', timestamp) as hour,
                SUM(count_in) as total_in,
                SUM(count_out) as total_out,
                MAX(current_occupancy) as max_occupancy,
                AVG(current_occupancy) as avg_occupancy
            FROM counts
            WHERE timestamp BETWEEN ? AND ?
            GROUP BY strftime('%H', timestamp)
            ORDER BY hour
        """, (start.isoformat(), end.isoformat())) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_daily_stats(start_date: datetime, days: int = 7):
    """Holt tägliche Statistiken für mehrere Tage."""
    start = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=days)

    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT
                date(timestamp) as date,
                SUM(count_in) as total_in,
                SUM(count_out) as total_out,
                MAX(current_occupancy) as max_occupancy,
                AVG(current_occupancy) as avg_occupancy
            FROM counts
            WHERE timestamp BETWEEN ? AND ?
            GROUP BY date(timestamp)
            ORDER BY date
        """, (start.isoformat(), end.isoformat())) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_monthly_stats(year: int, month: int):
    """Holt Statistiken für einen Monat."""
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
                SUM(count_in) as total_in,
                SUM(count_out) as total_out,
                MAX(current_occupancy) as max_occupancy
            FROM counts
            WHERE timestamp BETWEEN ? AND ?
            GROUP BY date(timestamp)
            ORDER BY date
        """, (start.isoformat(), end.isoformat())) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
