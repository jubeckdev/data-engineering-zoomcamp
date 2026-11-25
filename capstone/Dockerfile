FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY code ./code
COPY dbt ./dbt
COPY dashboard/template.html ./dashboard/template.html
RUN mkdir -p runtime evidence
ENV PYTHONUNBUFFERED=1 PREFECT_SERVER_ANALYTICS_ENABLED=false PREFECT_HOME=/tmp/zoomcamp-prefect
CMD ["python", "code/pipeline.py"]
