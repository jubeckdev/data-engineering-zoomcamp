FROM python:3.13
WORKDIR /app
ENV PYTHONUNBUFFERED=1 DLT_TELEMETRY=false
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY *.py queries.sql ./
CMD ["python", "taxi_pipeline.py"]
