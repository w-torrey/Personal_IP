# Build the React frontend
FROM node:22-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Run the FastAPI backend, which also serves the built frontend
FROM python:3.12-slim
WORKDIR /app
COPY reqs.txt ./
RUN pip install --no-cache-dir -r reqs.txt
COPY backend/ ./backend/
COPY docs/schema.sql ./docs/schema.sql
COPY --from=frontend /app/frontend/dist ./frontend/dist

WORKDIR /app/backend
# Render sets PORT; default to 8000 elsewhere
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
