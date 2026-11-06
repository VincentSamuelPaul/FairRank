FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/tmp

WORKDIR /app

COPY requirements.txt requirements-dev.txt ./
# Dev requirements include pytest so the same image runs tests; harmless in prod.
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY . .
# Writable for the dev override's non-root user; named volumes inherit this on first creation.
RUN mkdir -p /app/media /app/staticfiles && chmod 777 /app/media /app/staticfiles

EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
