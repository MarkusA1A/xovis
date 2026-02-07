import httpx
import logging
from typing import Optional, Dict, Any
from config import (
    XOVIS_BASE_URL, XOVIS_USERNAME, XOVIS_PASSWORD,
    XOVIS_API_COUNT, XOVIS_API_LINES, XOVIS_API_LIVE
)

logger = logging.getLogger(__name__)


class XovisClient:
    """Client für die Kommunikation mit dem Xovis PC2SE Sensor."""

    def __init__(self):
        self.base_url = XOVIS_BASE_URL
        self.auth = (XOVIS_USERNAME, XOVIS_PASSWORD)
        self._current_in = 0
        self._current_out = 0
        self._occupancy = 0

    async def _request(self, endpoint: str) -> Optional[Dict[str, Any]]:
        """Führt einen HTTP-Request zum Sensor aus."""
        url = f"{self.base_url}{endpoint}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, auth=self.auth)
                response.raise_for_status()

                content_type = response.headers.get("content-type", "")
                if "json" in content_type:
                    return response.json()
                elif "xml" in content_type:
                    return self._parse_xml(response.text)
                else:
                    return {"raw": response.text}

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP Fehler bei {url}: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"Verbindungsfehler zu {url}: {e}")
        except Exception as e:
            logger.error(f"Unbekannter Fehler bei {url}: {e}")

        return None

    def _parse_xml(self, xml_text: str) -> Dict[str, Any]:
        """Einfacher XML-Parser für Xovis-Daten."""
        import re
        result: Dict[str, Any] = {}

        # Versuche, count_in, count_out, occupancy aus XML zu extrahieren
        patterns = {
            "count_in": r"<(?:in|countIn|forward)[^>]*>(\d+)</",
            "count_out": r"<(?:out|countOut|backward)[^>]*>(\d+)</",
            "occupancy": r"<(?:occupancy|current|fill)[^>]*>(\d+)</",
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, xml_text, re.IGNORECASE)
            if match:
                result[key] = int(match.group(1))

        return result if result else {"raw": xml_text}

    async def get_live_count(self) -> Dict[str, Any]:
        """Holt die aktuellen Live-Zähldaten."""
        # Versuche verschiedene Endpoints
        endpoints = [
            XOVIS_API_LIVE,
            XOVIS_API_COUNT,
            "/api/v5/occupancy",
            "/api/counts",
            "/counts",
        ]

        for endpoint in endpoints:
            data = await self._request(endpoint)
            if data and not data.get("raw"):
                count_in = data.get("count_in", data.get("in", data.get("forward", 0)))
                count_out = data.get("count_out", data.get("out", data.get("backward", 0)))
                occupancy = data.get("occupancy", data.get("current", count_in - count_out))

                self._current_in = count_in
                self._current_out = count_out
                self._occupancy = max(0, occupancy)

                return {
                    "count_in": self._current_in,
                    "count_out": self._current_out,
                    "occupancy": self._occupancy,
                    "endpoint": endpoint
                }

        # Fallback: Simulierte Daten für Testzwecke
        logger.warning("Keine Verbindung zum Sensor - verwende Testdaten")
        return self._get_simulated_data()

    def _get_simulated_data(self) -> Dict[str, Any]:
        """Generiert simulierte Testdaten wenn Sensor nicht erreichbar."""
        import random
        from datetime import datetime

        hour = datetime.now().hour

        # Simuliere typisches Besuchermuster in einem Ärztehaus
        if 8 <= hour <= 12:  # Morgendliche Stoßzeit
            base_in = random.randint(5, 15)
            base_out = random.randint(3, 10)
        elif 14 <= hour <= 17:  # Nachmittags
            base_in = random.randint(3, 10)
            base_out = random.randint(3, 8)
        else:  # Ruhige Zeiten
            base_in = random.randint(0, 3)
            base_out = random.randint(0, 3)

        self._current_in += base_in
        self._current_out += base_out
        self._occupancy = max(0, self._current_in - self._current_out)

        return {
            "count_in": self._current_in,
            "count_out": self._current_out,
            "occupancy": self._occupancy,
            "simulated": True
        }

    async def get_lines(self) -> Optional[Dict[str, Any]]:
        """Holt Informationen über konfigurierte Zähllinien."""
        return await self._request(XOVIS_API_LINES)

    async def check_connection(self) -> bool:
        """Prüft die Verbindung zum Sensor."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(self.base_url, auth=self.auth)
                return response.status_code < 400
        except Exception:
            return False


# Singleton-Instanz
xovis_client = XovisClient()
