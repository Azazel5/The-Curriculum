FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System deps (kept minimal; psycopg2-binary doesn't require build deps)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

# Fly routes 80/443 -> internal 8080 by default
EXPOSE 8080

# Gunicorn entrypoint (production)
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "wsgi:app"]

