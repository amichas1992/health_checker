# Use a small, supported Python image with the runtime
FROM python:3.12-slim

# Create non-root user
RUN useradd -m appuser

WORKDIR /app

# Copy dependencies first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY health_checker.py .

# Create logs dir (optional)
RUN mkdir -p /app/logs && chown appuser:appuser /app/logs

USER appuser

# Default command (reads env vars for URLs etc.)
CMD ["python", "health_checker.py"]
