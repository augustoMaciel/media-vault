FROM python:3.12-slim

# Predictable Python behavior in containers.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLASK_APP=wsgi

WORKDIR /app

# Dependencies first (cached layer; only re-runs when requirements.txt changes).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application source.
COPY . .

EXPOSE 5000

# Apply migrations, then serve. `flask db upgrade` is a no-op if already current.
CMD ["sh", "-c", "flask db upgrade && gunicorn -b 0.0.0.0:5000 wsgi:app"]
