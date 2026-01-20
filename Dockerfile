FROM python:3.12-slim

WORKDIR /app


RUN apt-get update && apt-get install -y \
    ffmpeg \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY src/hometeamproj/config.ini src/hometeamproj/config.ini

ENV PYTHONPATH=/app/src

CMD ["python", "-m", "hometeamproj.main"]
