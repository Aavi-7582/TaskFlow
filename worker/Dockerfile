FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY worker ./worker

WORKDIR /app/worker

CMD ["python", "worker.py"]