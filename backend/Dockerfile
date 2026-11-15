FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.lock.txt /app/backend/requirements.lock.txt
RUN pip install --no-cache-dir -r backend/requirements.lock.txt
COPY backend /app/backend
COPY dist /app/dist
# Prepare data with python -m backend.acquire before running, or mount a verified data volume.
VOLUME /app/data
EXPOSE 8000
CMD ["uvicorn","backend.server:app","--host","0.0.0.0","--port","8000","--workers","1"]
