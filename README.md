# Xovis Besucherzähler Dashboard

Web-Dashboard zur Visualisierung der Besucherzahlen vom Xovis PC2SE 3D Personenzähler.

## Features

- **Live-Anzeige**: Aktuelle Besucherzahl im Gebäude
- **Tagesverlauf**: Stündliche Statistiken als Liniendiagramm
- **Wochenstatistik**: Tägliche Vergleiche der letzten 7 Tage
- **Monatsübersicht**: Komplette Monatsstatistik als Balkendiagramm
- **Responsive Design**: Funktioniert auf Desktop, Tablet und Smartphone
- **Dark Mode**: Automatische Anpassung an Systemeinstellungen

## Voraussetzungen

- Docker und Docker Compose
- Netzwerkzugang zum Xovis Sensor (IP: 10.13.1.165)

## Installation auf dem NUC (Proxmox/Docker)

### 1. Projekt auf den Server kopieren

```bash
# Per SCP
scp -r xovis-dashboard user@nuc-ip:/opt/

# Oder per Git
git clone <repo-url> /opt/xovis-dashboard
```

### 2. Konfiguration anpassen

Bearbeite `docker-compose.yml` falls nötig:

```yaml
environment:
  - XOVIS_SENSOR_IP=10.13.1.165    # IP des Sensors
  - XOVIS_SENSOR_PORT=80           # Port (Standard: 80)
  - XOVIS_USERNAME=admin           # Benutzername
  - XOVIS_PASSWORD=pass            # Passwort
  - POLL_INTERVAL=60               # Abfrage-Intervall in Sekunden
```

### 3. Subdomain einrichten

Bearbeite `nginx/nginx.conf` und ersetze:
```
server_name zaehler.aerztehaus.de;
```
mit deiner tatsächlichen Subdomain.

### 4. Starten

**Einfache Version (ohne HTTPS):**
```bash
cd /opt/xovis-dashboard
docker-compose -f docker-compose.simple.yml up -d --build
```

**Mit Nginx Reverse Proxy:**
```bash
cd /opt/xovis-dashboard
docker-compose up -d --build
```

### 5. Zugriff

- Ohne Nginx: `http://<nuc-ip>:8080`
- Mit Nginx: `http://zaehler.aerztehaus.de`

## SSL-Zertifikat einrichten (optional)

### Mit Let's Encrypt:

```bash
# Certbot installieren
apt install certbot

# Zertifikat anfordern
certbot certonly --webroot -w /var/www/certbot -d zaehler.aerztehaus.de

# Zertifikate kopieren
cp /etc/letsencrypt/live/zaehler.aerztehaus.de/fullchain.pem nginx/ssl/
cp /etc/letsencrypt/live/zaehler.aerztehaus.de/privkey.pem nginx/ssl/

# HTTPS in nginx.conf aktivieren (Kommentare entfernen)
# Container neu starten
docker-compose restart nginx
```

## API-Endpoints

| Endpoint | Beschreibung |
|----------|-------------|
| `GET /api/live` | Aktuelle Live-Zähldaten |
| `GET /api/status` | Sensor-Verbindungsstatus |
| `GET /api/stats/today` | Stündliche Statistik für heute |
| `GET /api/stats/week` | Tägliche Statistik der letzten 7 Tage |
| `GET /api/stats/month` | Statistik des aktuellen Monats |
| `GET /api/stats/month/{year}/{month}` | Statistik für einen bestimmten Monat |

## Xovis Sensor API

Falls die Standard-Endpoints nicht funktionieren, muss die API-Konfiguration angepasst werden.
Logge dich in die Web-Oberfläche des Sensors ein: `http://10.13.1.165`

Die verfügbaren Endpoints findest du in der Sensor-Konfiguration unter "Data Push" oder "API".

Passe dann die Umgebungsvariablen an:
```yaml
- XOVIS_API_LIVE=/api/v5/live
- XOVIS_API_COUNT=/api/v5/counts
- XOVIS_API_LINES=/api/v5/lines
```

## Fehlerbehebung

### Sensor nicht erreichbar

1. Prüfe die Netzwerkverbindung: `ping 10.13.1.165`
2. Prüfe den Sensor-Webzugang: `curl http://10.13.1.165`
3. Prüfe Benutzername/Passwort

### Keine Daten im Dashboard

1. Prüfe die Container-Logs: `docker-compose logs -f xovis-dashboard`
2. Prüfe den API-Status: `curl http://localhost:8080/api/status`

### Container neu starten

```bash
docker-compose down
docker-compose up -d --build
```

## Datenbankzugriff

Die Zähldaten werden in einer SQLite-Datenbank gespeichert:

```bash
# Datenbank-Volume finden
docker volume inspect xovis-dashboard-data

# Daten exportieren
docker exec xovis-dashboard sqlite3 /data/xovis_counts.db ".dump" > backup.sql
```

## Lizenz

Dieses Projekt wurde für das Ärztehaus erstellt.
