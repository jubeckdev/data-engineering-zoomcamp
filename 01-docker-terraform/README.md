# Module 1 Homework: Docker & SQL

## Question 1: Understanding Docker images

**Answer:** pip version `26.2.1`.

Start a container with the Python 3.13 image and Bash as the entrypoint:

```bash
docker run -it --rm --entrypoint bash python:3.13
```

Inside the container, check the pip version:

```bash
pip --version
```

Output:

```text
pip 26.2.1 from /usr/local/lib/python3.13/site-packages/pip (python 3.13)
```

The version differs from the homework options because the image has been updated since the live cohort.

## Question 2: Understanding Docker networking and docker-compose

**Answer:** `postgres:5432` and `db:5432` (options 4 and 5).

pgAdmin connects to PostgreSQL over the Compose network using the internal
container port `5432`. Both the container name `postgres` and the service name
`db` resolve to the database container.

The port mapping `5433:5432` exposes PostgreSQL on `localhost:5433` on the host
machine. Inside the pgAdmin container, `localhost` refers to pgAdmin itself.

## Reproduce the Docker and SQL work

Source: [2026 Module 1 homework](https://github.com/DataTalksClub/data-engineering-zoomcamp/blob/main/cohorts/2026/01-docker-terraform/homework.md).

From the repository root, with Docker Desktop running:

```bash
cd 01-docker-terraform/code
docker compose run --build --rm ingest
```

This starts PostgreSQL, builds a Python container, downloads the November 2025
Green Taxi Parquet file and the zone lookup, prints input SHA-256 checksums,
loads `trips` and `zones`, and executes `queries.sql`. Dependencies are pinned
in `requirements.txt`. Re-running replaces these two homework tables in a
transaction; use this database only for this exercise.

To run the queries again without downloading or loading:

```bash
docker compose exec -T db psql -U postgres -d ny_taxi < queries.sql
```

Optional pgAdmin interface:

```bash
docker compose --profile ui up -d pgadmin
```

Open http://localhost:8080 and log in with `pgadmin@pgadmin.com` / `pgadmin`.
Register a server using host `db`, port `5432`, database `ny_taxi`, and username
and password `postgres`. From a client running on your Mac, use
`localhost:5433` instead. Ports are bound only to localhost.

Stop the services while keeping the database volume:

```bash
docker compose down
```

## Question 3: Counting short trips

**Answer:** 8,007 trips.

Filter November pickups with an exclusive December 1 boundary and count distances at most one mile.

```sql
-- Q3: Include November pickups. The upper date boundary is exclusive.
SELECT COUNT(*) AS q3_short_trips
FROM trips
WHERE lpep_pickup_datetime >= TIMESTAMP '2025-11-01'
  AND lpep_pickup_datetime < TIMESTAMP '2025-12-01'
  AND trip_distance <= 1;
```

## Question 4: Longest trip

**Answer:** 2025-11-14 (88.03 miles).

Group by pickup day, exclude distances of 100 miles or more, then sort daily maximum distances.

```sql
-- Q4: Find the maximum valid distance for each pickup day.
SELECT CAST(lpep_pickup_datetime AS date) AS q4_pickup_day,
       MAX(trip_distance) AS longest_distance
FROM trips
WHERE trip_distance < 100
GROUP BY 1
ORDER BY longest_distance DESC, q4_pickup_day
LIMIT 1;
```

## Question 5: Biggest pickup zone

**Answer:** East Harlem North ($9,281.92).

Join pickup IDs to zone names and sum total charges on November 18.

```sql
-- Q5: Sum charges by pickup zone on November 18.
SELECT z."Zone" AS q5_pickup_zone, SUM(t.total_amount) AS total_amount
FROM trips t JOIN zones z ON t."PULocationID" = z."LocationID"
WHERE t.lpep_pickup_datetime >= TIMESTAMP '2025-11-18'
  AND t.lpep_pickup_datetime < TIMESTAMP '2025-11-19'
GROUP BY z."Zone"
ORDER BY total_amount DESC
LIMIT 1;
```

## Question 6: Largest tip

**Answer:** Yorkville West ($81.89).

Filter East Harlem North pickups in November, join drop-off names, and compare the largest individual tips.

```sql
-- Q6: Largest individual tip, rather than the sum of tips.
SELECT d."Zone" AS q6_dropoff_zone, MAX(t.tip_amount) AS largest_tip
FROM trips t
JOIN zones p ON t."PULocationID" = p."LocationID"
JOIN zones d ON t."DOLocationID" = d."LocationID"
WHERE p."Zone" = 'East Harlem North'
  AND t.lpep_pickup_datetime >= TIMESTAMP '2025-11-01'
  AND t.lpep_pickup_datetime < TIMESTAMP '2025-12-01'
GROUP BY d."Zone"
ORDER BY largest_tip DESC
LIMIT 1;
```

## Question 7: Terraform workflow

**Answer:** option 4.

```bash
terraform init
terraform apply -auto-approve
terraform destroy
```

`init` installs providers and initializes the backend. `apply -auto-approve`
creates and executes a plan without an approval prompt. `destroy` removes the
resources tracked by this Terraform configuration.

## Terraform implementation

`code/terraform/main.tf` defines a private GCS bucket and a BigQuery dataset.
It uses an existing project, EU data locations, and Application Default
Credentials. It refuses to delete nonempty resources by default.

Terraform can run through Docker, so a host installation is optional:

```bash
cd terraform  # from 01-docker-terraform/code
cp terraform.tfvars.example terraform.tfvars
# Set project_id in terraform.tfvars to your own existing GCP project.
# Install the Google Cloud CLI, then authenticate:
gcloud auth application-default login

# Define a wrapper that mounts the configuration and local credentials.
terraform() {
  docker run --rm -it \
    -v "$PWD:/work" \
    -v "$HOME/.config/gcloud:/root/.config/gcloud:ro" \
    -w /work hashicorp/terraform:1.13.5 "$@"
}
terraform init
terraform fmt -check
terraform validate
terraform plan -out=deployment.tfplan
terraform apply deployment.tfplan
# When finished with the cloud resources:
terraform destroy
```

The project needs billing and the Cloud Storage and BigQuery APIs enabled,
and credentials with permission to create these resources. The bucket name
is derived from the project ID. State, credentials, and local variable values
must not be committed. The provider lock file is committed for reproducibility.

**Deployment status:** configuration prepared; actual GCP creation is pending
an authenticated Google Cloud project.

## Verification

The Docker pipeline was run against PostgreSQL 17. All four SQL queries were
also executed through `psql`. Terraform initialization, `fmt -check`, and
`validate` passed. Cloud apply remains pending project configuration. Q1
preserves the pip version you observed earlier; floating image tags can change.
