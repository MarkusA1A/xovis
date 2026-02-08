FROM python:3.11-slim-bullseye

WORKDIR /app

# Abhängigkeiten installieren
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Backend-Code kopieren
COPY *.py ./

# Frontend-Verzeichnis erstellen
RUN mkdir -p /app/frontend

# Daten-Verzeichnis erstellen
RUN mkdir -p /data

# Port freigeben
EXPOSE 8000

# Starten
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
