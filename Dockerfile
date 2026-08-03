# Kastara Finance — Railway deploy image (docs/deploy.md §7).
# Multi-stage: build Vue frontend once, ship it inside the Python image that
# actually runs (web/app.py sudah menyajikan web/frontend/dist/ langsung,
# lihat komentar SPA catch-all di app.py -- SATU proses/port, tidak butuh
# Vite dev server di production).

FROM node:22-alpine AS frontend-build
WORKDIR /app/web/frontend
COPY web/frontend/package*.json ./
RUN npm ci
COPY web/frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
# Timpa dist/ lokal (kalau ada) dengan hasil build fresh dari stage 1 --
# jangan pernah kirim dist lama/basi ke image.
COPY --from=frontend-build /app/web/frontend/dist web/frontend/dist

ENV PYTHONUNBUFFERED=1

# Railway inject $PORT saat runtime -- jangan hardcode port lain di sini.
# --timeout 300: /api/run_daily_now (trigger pipeline penuh dari Snapshot,
# lihat ROADMAP.md 28 Jul 2026) bisa berjalan lama (network fetch semua
# sumber) -- default gunicorn 30s akan membunuh request itu di tengah jalan.
# --workers 2: satu worker bisa sibuk lama (endpoint di atas) tanpa
# memblokir semua request lain; SQLite single-writer tetap aman krn
# db/connection.py sudah pakai busy_timeout=5000 (lihat ARCHITECTURE §6.1).
CMD ["sh", "-c", "gunicorn web.app:app --bind 0.0.0.0:${PORT:-8080} --workers 2 --timeout 300"]
