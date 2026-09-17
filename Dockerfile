FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot/ ./bot/
COPY main.py .

RUN useradd --create-home --uid 1000 bot && mkdir -p /app/data && chown -R bot:bot /app
USER bot

CMD ["python", "main.py"]
