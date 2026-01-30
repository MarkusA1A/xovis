import logging
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from database import (
    init_db, save_count, get_latest_count,
    get_hourly_stats, get_daily_stats, get_monthly_stats,
    update_live_count, get_live_count
)

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup und Shutdown Handler."""
    await init_db()
    logger.info("Datenbank initialisiert")
    logger.info("Warte auf Daten vom Xovis-Sensor (Data Push)...")
    yield
    logger.info("Server beendet")


# FastAPI App
app = FastAPI(
    title="Xovis Besucherzähler Dashboard",
    description="Visualisierung der Besucherzahlen im Ärztehaus",
    version="2.0.0",
    lifespan=lifespan
)

# CORS
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
    """Hauptseite."""
    return FileResponse("/app/frontend/index.html")


# ============== WEBHOOK für Xovis Data Push ==============

@app.post("/api/webhook")
async def webhook_xovis(request: Request):
    """Empfängt Live-Daten vom Xovis-Sensor."""
    try:
        content_type = request.headers.get("content-type", "")
        body = await request.body()
        body_text = body.decode("utf-8")

        logger.info(f"Webhook empfangen - Content-Type: {content_type}")
        logger.info(f"Body: {body_text}")

        import json
        data = json.loads(body_text)

        # Xovis Live Data Format parsen
        count_in = 0
        count_out = 0

        # Events aus frames extrahieren
        live_data = data.get("live_data", data)
        frames = live_data.get("frames", [])

        for frame in frames:
            events = frame.get("events", [])
            for event in events:
                if event.get("category") == "COUNT" and event.get("type") == "COUNT_INCREMENT":
                    attrs = event.get("attributes", {})
                    direction = attrs.get("direction", "")

                    if direction == "fw" or direction == "forward" or direction == 1:
                        count_in += 1
                    elif direction == "bw" or direction == "backward" or direction == -1 or direction == 0:
                        count_out += 1

        # Aktuelle Werte aus DB holen und inkrementieren
        live = await get_live_count()
        new_in = live.get("count_in", 0) + count_in
        new_out = live.get("count_out", 0) + count_out
        occupancy = max(0, new_in - new_out)

        logger.info(f"Events: +{count_in} IN, +{count_out} OUT | Gesamt: {new_in} IN, {new_out} OUT, Belegung: {occupancy}")

        # Speichern
        await update_live_count(new_in, new_out, occupancy)

        return {"status": "ok", "added_in": count_in, "added_out": count_out}

    except Exception as e:
        logger.error(f"Webhook Fehler: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"status": "error", "message": str(e)}


def parse_xovis_xml(text: str) -> Dict[str, Any]:
    """Parst Xovis XML-Daten."""
    import re
    result = {"raw": text}

    # Verschiedene XML-Patterns für Xovis
    patterns = [
        (r"<fw[^>]*>(\d+)</fw>", "fw"),
        (r"<bw[^>]*>(\d+)</bw>", "bw"),
        (r"<forward[^>]*>(\d+)</forward>", "forward"),
        (r"<backward[^>]*>(\d+)</backward>", "backward"),
        (r"<in[^>]*>(\d+)</in>", "in"),
        (r"<out[^>]*>(\d+)</out>", "out"),
        (r"<cnt[^>]*fw[^>]*>(\d+)</", "fw"),
        (r"<cnt[^>]*bw[^>]*>(\d+)</", "bw"),
        (r"cnt_in=\"(\d+)\"", "cnt_in"),
        (r"cnt_out=\"(\d+)\"", "cnt_out"),
        (r"\"fw\"\s*:\s*(\d+)", "fw"),
        (r"\"bw\"\s*:\s*(\d+)", "bw"),
    ]

    for pattern, key in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result[key] = int(match.group(1))

    return result


def extract_count(data: Dict, keys: list) -> int:
    """Extrahiert Zählwert aus verschiedenen möglichen Schlüsseln."""
    if not isinstance(data, dict):
        return 0

    # Direkte Schlüssel prüfen
    for key in keys:
        if key in data:
            try:
                return int(data[key])
            except (ValueError, TypeError):
                pass

    # In verschachtelten Strukturen suchen
    for value in data.values():
        if isinstance(value, dict):
            result = extract_count(value, keys)
            if result > 0:
                return result
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    result = extract_count(item, keys)
                    if result > 0:
                        return result
    return 0


# ============== API für Dashboard ==============

@app.get("/api/live")
async def api_get_live():
    """Aktuelle Zähldaten."""
    live = await get_live_count()
    return {
        "current": {
            "count_in": live.get("count_in", 0),
            "count_out": live.get("count_out", 0),
            "occupancy": live.get("occupancy", 0),
        },
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/status")
async def get_status():
    """Status des Systems."""
    live = await get_live_count()
    last_update = live.get("last_update")

    sensor_active = False
    if last_update:
        try:
            last_dt = datetime.fromisoformat(last_update)
            sensor_active = (datetime.now() - last_dt).seconds < 300
        except:
            pass

    return {
        "sensor_connected": sensor_active,
        "last_update": last_update,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/stats/today")
async def get_today_stats():
    """Stündliche Statistiken für heute."""
    today = datetime.now()
    stats = await get_hourly_stats(today)
    return {"date": today.strftime("%Y-%m-%d"), "hours": stats}


@app.get("/api/stats/week")
async def get_week_stats():
    """Statistiken der letzten 7 Tage."""
    start = datetime.now() - timedelta(days=6)
    stats = await get_daily_stats(start, 7)
    return {
        "start_date": start.strftime("%Y-%m-%d"),
        "end_date": datetime.now().strftime("%Y-%m-%d"),
        "days": stats
    }


@app.get("/api/stats/month")
async def get_current_month_stats():
    """Statistiken des aktuellen Monats."""
    now = datetime.now()
    stats = await get_monthly_stats(now.year, now.month)
    return {"year": now.year, "month": now.month, "days": stats}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
