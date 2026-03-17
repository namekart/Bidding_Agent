# ---------- Base ----------
FROM python:3.11-slim

# ---------- Env ----------
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# ---------- System deps ----------
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    gcc \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

# ---------- Workdir ----------
WORKDIR /app

# ---------- Install deps ----------
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---------- Copy project ----------
COPY app ./app
COPY .env .env

# if parquet/sql outside app, copy them also
# COPY data ./data

# ---------- Expose ----------
EXPOSE 8000

# ---------- Start server ----------
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "120"]