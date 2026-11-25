.PHONY: help check check-azure module1-run module1-query module1-stop module2-up module2-stop module3-run module4-load module4-build module5-verify streaming-up streaming-stop dlt-run spark-run

COMPOSE = docker compose -f 01-docker-terraform/code/compose.yaml

help:
	@printf '%s\n' 'make capstone-dashboard View the included dashboard locally' 'make capstone-local     Run extraction and dbt locally (requires capstone venv)' 'make capstone-cloud     Run the Azure pipeline (requires deployed infrastructure)'
	@printf '%s\n' 'make check         Check local prerequisites' 'make check-azure   Also check Azure CLI and login' 'make module1-run   Build, download, and ingest Module 1 data' 'make module1-query Run the Module 1 SQL queries' 'make module1-stop  Stop Module 1 services; retain database volume'
	@printf '%s\n' 'make module2-up    Start local Kestra and PostgreSQL' 'make module2-stop Stop the orchestration stack' 'make module3-run   Verify six warehouse source files locally' 'make module4-load  Load all fixed dbt source releases (requires module venv)' 'make module4-build Build and test dbt production models' 'make module5-verify Check the saved Bruin replay fixture' 'make streaming-up Start Redpanda, Flink and PostgreSQL' 'make streaming-stop Stop the streaming stack' 'make dlt-run       Execute the paginated API pipeline' 'make spark-run     Execute the Spark homework'

check:
	python3 scripts/check_environment.py

check-azure:
	python3 scripts/check_environment.py --azure

module1-run:
	$(COMPOSE) run --build --rm ingest

module1-query:
	$(COMPOSE) up -d --wait db
	$(COMPOSE) exec -T db psql -v ON_ERROR_STOP=1 -U postgres -d ny_taxi < 01-docker-terraform/code/queries.sql

module1-stop:
	$(COMPOSE) down

module2-up:
	docker compose -f 02-workflow-orchestration/compose.yaml up --build -d

module2-stop:
	docker compose -f 02-workflow-orchestration/compose.yaml down

module3-run:
	docker compose -f 03-data-warehouse/compose.yaml run --build --rm verify

module4-load:
	04-analytics-engineering/.venv/bin/python 04-analytics-engineering/code/load_sources.py

module4-build:
	cd 04-analytics-engineering/taxi_rides_ny && ../.venv/bin/dbt build --target prod --profiles-dir .
	04-analytics-engineering/.venv/bin/python 04-analytics-engineering/code/answers.py

module5-verify:
	04-analytics-engineering/.venv/bin/python 05-data-platforms/verify.py

streaming-up:
	docker compose -f 07-streaming/compose.yaml build jobmanager
	docker compose -f 07-streaming/compose.yaml up -d

streaming-stop:
	docker compose -f 07-streaming/compose.yaml down

dlt-run:
	docker compose -f workshops/dlt/compose.yaml run --build --rm pipeline python taxi_pipeline.py

spark-run:
	docker compose -f 06-batch/compose.yaml run --build --rm spark

.PHONY: capstone-local capstone-cloud capstone-dashboard
capstone-local:
	capstone/.venv/bin/python capstone/code/pipeline.py --local

capstone-cloud:
	capstone/.venv/bin/python capstone/code/pipeline.py

capstone-dashboard:
	python3 -m http.server 8095 --directory capstone/dashboard --bind 127.0.0.1
