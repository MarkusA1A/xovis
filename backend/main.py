import asyncio
import logging
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import POLL_INTERVAL
from database import (
    init_db, save_count, get_latest_count,
    get_hourly_stats, get_daily_stats, get_monthly_stats
)
from xovis_client import xovis_client

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Scheduler für periodisches Polling
scheduler = AsyncIOScheduler()

async def poll_sensor():
    """Holt Daten vom Sensor und speichert sie."""
    try:
        data = await xovis_client.get_live_count()
        await save_count(
            data.get("count_in", 0),
            data.get("count_out", 0),
            data.get("occupancy", 0)
        )
        logger.info(f"Daten gespeichert: IN={data.get('count_in')}, OUT={data.get('count_out')}, Aktuell={data.get('occupancy')}")
    except Exception as e:
        logger.error(f"Fehler beim Polling: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup und Shutdown Handler."""
    # Startup
    await init_db()
    logger.info("Datenbank initialisiert")

    # Sensor-Verbindung prüfen
    connected = await xovis_client.check_connection()
    if connected:
        logger.info("Verbindung zum Xovis-Sensor hergestellt")
    else:
        logger.warning("Keine Verbindung zum Sensor - Testmodus aktiv")

    # Scheduler starten
    scheduler.add_job(poll_sensor, "interval", seconds=POLL_INTERVAL)
    scheduler.start()
    logger.info(f"Polling gestartet (alle {POLL_INTERVAL} Sekunden)")

    # Erste Abfrage sofort
    await poll_sensor()

    yield

    # Shutdown
    scheduler.shutdown()
    logger.info("Scheduler beendet")

# FastAPI App
app = FastAPI(
    title="Xovis Besucherzähler Dashboard",
    description="Visualisierung der Besucherzahlen im Ärztehaus",
    version="1.0.0",
    lifespan=lifespan
)

# CORS für lokale Entwicklung
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Statische Dateien
app.mount("/static", StaticFiles(directory="/app/frontend"), name="static")

@app.get("/")
async def root():
    """Hauptseite - liefert das Dashboard."""
    return FileResponse("/app/frontend/index.html")

@app.get("/api/live")
async def get_live():
    """Aktuelle Live-Zähldaten."""
    data = await xovis_client.get_live_count()
    latest = await get_latest_count()

    return {
        "current": data,
        "last_saved": latest,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/status")
async def get_status():
    """Status der Sensor-Verbindung."""
    connected = await xovis_client.check_connection()
    return {
        "sensor_connected": connected,
        "sensor_ip": xovis_client.base_url,
        "poll_interval": POLL_INTERVAL,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/stats/today")
async def get_today_stats():
    """Stündliche Statistiken für heute."""
    today = datetime.now()
    stats = await get_hourly_stats(today)
    return {
        "date": today.strftime("%Y-%m-%d"),
        "hours": stats
    }

@app.get("/api/stats/week")
async def get_week_stats():
    """Tägliche Statistiken der letzten 7 Tage."""
    start = datetime.now() - timedelta(days=6)
    stats = await get_daily_stats(start, 7)
    return {
        "start_date": start.strftime("%Y-%m-%d"),
        "end_date": datetime.now().strftime("%Y-%m-%d"),
        "days": stats
    }

@app.get("/api/stats/month/{year}/{month}")
async def get_month_stats(year: int, month: int):
    """Statistiken für einen bestimmten Monat."""
    if not (1 <= month <= 12):
        raise HTTPException(status_code=400, detail="Ungültiger Monat")
    if not (2020 <= year <= 2030):
        raise HTTPException(status_code=400, detail="Ungültiges Jahr")

    stats = await get_monthly_stats(year, month)
    return {
        "year": year,
        "month": month,
        "days": stats
    }

@app.get("/api/stats/month")
async def get_current_month_stats():
    """Statistiken für den aktuellen Monat."""
    now = datetime.now()
    return await get_month_stats(now.year, now.month)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
