FROM python:3.13-slim
RUN apt-get update && apt-get install -y --no-install-recommends openjdk-21-jre-headless && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir pyspark==4.0.1
WORKDIR /app
COPY batch.py .
ENV SPARK_LOCAL_IP=127.0.0.1
CMD ["python", "batch.py"]
