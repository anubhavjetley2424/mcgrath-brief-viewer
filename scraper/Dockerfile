# Cloud Run Jobs image — runs one scraper per invocation.
# Tiny Python image; no Chromium needed because every scraper uses
# urllib + JSON/HTML extraction (no browser engine).

FROM python:3.11-slim

# Set working dir
WORKDIR /app

# System deps — keep minimal. tzdata so cron times resolve to AEDT/AEST.
RUN apt-get update \
 && apt-get install -y --no-install-recommends tzdata ca-certificates \
 && rm -rf /var/lib/apt/lists/*

ENV TZ=Australia/Sydney
ENV PYTHONUNBUFFERED=1

# Copy requirements first so Docker layer cache survives code edits
COPY scraper/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy scrapers + orchestrator
COPY scripts/ /app/scripts/
COPY scraper/orchestrator.py /app/orchestrator.py

# Entry point — orchestrator reads the JOB env var and dispatches.
# Cloud Run Jobs sets JOB per-job via env override; locally:
#   docker run --rm -e JOB=domain-sale-farm -e SUPABASE_ANON_KEY=xxx <image>
ENTRYPOINT ["python", "/app/orchestrator.py"]
