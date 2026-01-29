import os
from dotenv import load_dotenv

load_dotenv()

# Xovis Sensor Konfiguration
XOVIS_SENSOR_IP = os.getenv("XOVIS_SENSOR_IP", "10.13.1.165")
XOVIS_SENSOR_PORT = os.getenv("XOVIS_SENSOR_PORT", "80")
XOVIS_USERNAME = os.getenv("XOVIS_USERNAME", "admin")
XOVIS_PASSWORD = os.getenv("XOVIS_PASSWORD", "pass")

# API Endpoints (können angepasst werden)
XOVIS_BASE_URL = f"http://{XOVIS_SENSOR_IP}:{XOVIS_SENSOR_PORT}"
XOVIS_API_COUNT = os.getenv("XOVIS_API_COUNT", "/api/v5/counts")
XOVIS_API_LINES = os.getenv("XOVIS_API_LINES", "/api/v5/lines")
XOVIS_API_LIVE = os.getenv("XOVIS_API_LIVE", "/api/v5/live")

# Datenbank
DATABASE_PATH = os.getenv("DATABASE_PATH", "/data/xovis_counts.db")

# Polling Intervall in Sekunden
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "60"))
