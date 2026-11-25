FROM kestra/kestra:v1.1
USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-psycopg2 ca-certificates \
    && rm -rf /var/lib/apt/lists/*
