FROM python:3.12-slim

# non-root user
RUN useradd -m appuser

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY health_checker.py .

USER appuser

# Default: CLI mode. To run web: pass MODE=web or argument "web"
CMD ["python", "health_checker.py"]
