FROM python:3.12-slim

# Keep bytecode out of the image and make logs stream rather than buffer, so
# platform log viewers show output in real time.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Don't run as root in production.
RUN useradd --create-home --uid 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Production default: no --reload (that spawns a file watcher and restarts on
# filesystem events). docker-compose overrides this with a --reload command for
# local development. Shell form so $PORT is expanded — hosting platforms assign
# it at runtime.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
