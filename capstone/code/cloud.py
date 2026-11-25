"""Keyless lake and Azure SQL access for the dedicated capstone resources."""
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re
import uuid

from azure.core.exceptions import ResourceExistsError
from azure.identity import AzureCliCredential, ManagedIdentityCredential
from azure.storage.blob import BlobServiceClient
import certifi
import duckdb
import pytds
from pytds.tds_base import Column
from pytds.tds_types import sql_type_by_declaration

from transform import ROOT, TABLES

_credential = None


def credential():
    global _credential
    if _credential is None:
        _credential = ManagedIdentityCredential(client_id=os.environ["AZURE_CLIENT_ID"]) if os.getenv("IDENTITY_ENDPOINT") else AzureCliCredential()
    return _credential


def config():
    path = ROOT / "config.local.json"
    values = json.loads(path.read_text()) if path.exists() else {}
    for key in ["storage_account", "sql_server", "sql_database"]:
        values[key] = os.getenv(key.upper(), values.get(key))
        if not values[key]:
            raise ValueError(f"Missing configuration: {key}")
    return values


def lake():
    return BlobServiceClient(f"https://{config()['storage_account']}.blob.core.windows.net", credential=credential())


def put(container, name, payload, overwrite=False):
    digest = hashlib.sha256(payload).hexdigest()
    blob = lake().get_blob_client(container, name)
    try:
        blob.upload_blob(payload, overwrite=overwrite, metadata={"sha256": digest})
    except ResourceExistsError:
        properties = blob.get_blob_properties()
        if properties.metadata.get("sha256") != digest or properties.size != len(payload):
            raise ValueError("Existing immutable lake object does not match its content")
    return digest


def sql_connection():
    settings = config()
    return pytds.connect(settings["sql_server"], database=settings["sql_database"],
        access_token_callable=lambda: credential().get_token("https://database.windows.net/.default").token,
        cafile=certifi.where(), validate_host=True, enc_login_only=False,
        login_timeout=60, timeout=120, autocommit=False)


def initialize_sql():
    """One-time owner action. The workload gets rights only in analytics."""
    # SQL's SID-based external user creation uses the application's client ID.
    # Azure RBAC uses its object/principal ID; those identifiers differ.
    principal = uuid.UUID(config()["identity_client_id"])
    sid = principal.bytes_le.hex()
    with sql_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("IF SCHEMA_ID('analytics') IS NULL EXEC('CREATE SCHEMA analytics')")
            cursor.execute("SELECT sid FROM sys.database_principals WHERE name='swiss-rail-pipeline'")
            existing = cursor.fetchone()
            if existing and bytes(existing[0]) != principal.bytes_le:
                legacy = uuid.UUID(config()["identity_principal_id"]).bytes_le
                if bytes(existing[0]) != legacy:
                    raise ValueError("Unexpected existing SQL identity; inspect before changing it")
                cursor.execute("DROP USER [swiss-rail-pipeline]")
            cursor.execute(f"IF DATABASE_PRINCIPAL_ID('swiss-rail-pipeline') IS NULL CREATE USER [swiss-rail-pipeline] WITH SID=0x{sid}, TYPE=E")
            cursor.execute("GRANT CREATE TABLE, CREATE VIEW TO [swiss-rail-pipeline]")
            cursor.execute("GRANT SELECT, INSERT, UPDATE, DELETE, ALTER, REFERENCES ON SCHEMA::analytics TO [swiss-rail-pipeline]")
        connection.commit()


def sql_type(name, kind):
    if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
        raise ValueError("Unexpected model column identifier")
    if kind == "VARCHAR":
        return "NVARCHAR(32)" if name in {"station_code", "canton"} else "NVARCHAR(4000)"
    if kind in {"INTEGER", "BIGINT", "DOUBLE"}:
        return {"INTEGER": "INT", "BIGINT": "BIGINT", "DOUBLE": "FLOAT"}[kind]
    if re.fullmatch(r"DECIMAL\((18|38),2\)", kind):
        return kind
    raise ValueError(f"Unsupported model type: {kind}")


def publish_sql(artifacts, run_id, source_hash):
    indexes = {"dim_station": ["station_code"], "fct_station_usage": ["observed_year", "station_code"], "mart_station_year": ["observed_year", "station_code"], "mart_canton_year": ["observed_year", "canton"], "mart_common_cohort_year": ["observed_year"]}
    counts = {}
    with duckdb.connect() as data, sql_connection() as connection:
        try:
            with connection.cursor() as cursor:
                cursor.execute("SET NOCOUNT ON")
                cursor.execute("DECLARE @result int; EXEC @result=sys.sp_getapplock @Resource='swiss_rail_publish', @LockMode='Exclusive', @LockOwner='Transaction', @LockTimeout=30000; SELECT @result")
                while cursor.description is None:
                    if not cursor.nextset():
                        raise RuntimeError("Warehouse lock did not return a status")
                if cursor.fetchone()[0] < 0:
                    raise RuntimeError("Another warehouse publication owns the lock")
                for table in TABLES:
                    relation = data.read_parquet(artifacts[table]["path"])
                    columns = relation.columns
                    definitions = ",".join(f"[{name}] {sql_type(name,str(kind))}" for name,kind in zip(columns,relation.types,strict=True))
                    stage = f"{table}_stage_{run_id.replace('-', '')[:12]}"
                    cursor.execute(f"CREATE TABLE analytics.[{stage}] ({definitions})")
                    rows = relation.fetchall()
                    # String column names make pytds assume every value is
                    # NVARCHAR. Supply the actual types for native numeric data.
                    metadata = [Column(name=name, type=sql_type_by_declaration(sql_type(name, str(kind))), flags=Column.fNullable)
                                for name, kind in zip(columns, relation.types, strict=True)]
                    cursor.copy_to(table_or_view=stage, schema="analytics", columns=metadata, data=rows, keep_nulls=True)
                    cursor.execute(f"SELECT COUNT(*) FROM analytics.[{stage}]")
                    counts[table] = cursor.fetchone()[0]
                    if counts[table] != artifacts[table]["rows"]:
                        raise ValueError(f"Warehouse row count mismatch: {table}")
                    keys = ",".join(f"[{key}]" for key in indexes[table])
                    cursor.execute(f"CREATE UNIQUE CLUSTERED INDEX [ix_{table}] ON analytics.[{stage}] ({keys})")
                    cursor.execute(f"DROP TABLE IF EXISTS analytics.[{table}]")
                    cursor.execute("EXEC sys.sp_rename %s, %s", (f"analytics.{stage}", table))
                cursor.execute("IF OBJECT_ID('analytics.published_snapshot') IS NULL CREATE TABLE analytics.published_snapshot (id int PRIMARY KEY, run_id nvarchar(36), source_hash char(64), published_at datetime2)")
                cursor.execute("DELETE FROM analytics.published_snapshot")
                cursor.execute("INSERT INTO analytics.published_snapshot VALUES (1,%s,%s,SYSUTCDATETIME())", (run_id,source_hash))
            connection.commit()
        except Exception:
            try:
                connection.rollback()
            except Exception:
                # A broken TDS connection can no longer acknowledge rollback.
                # Closing it aborts the transaction; preserve the original error.
                connection.close()
            raise
    return counts


def dashboard_data():
    """Read the dashboard's actual serving data back from Azure SQL."""
    result = {}
    with sql_connection() as connection:
        with connection.cursor() as cursor:
            for table in ["mart_station_year", "mart_canton_year", "mart_common_cohort_year", "published_snapshot"]:
                cursor.execute(f"SELECT * FROM analytics.[{table}]")
                names = [c[0] for c in cursor.description]
                result[table] = [dict(zip(names,row,strict=True)) for row in cursor.fetchall()]
    result["generated_at"] = datetime.now(timezone.utc).isoformat()
    result["source"] = "SBB Personenverkehr — data.sbb.ch, passagierfrequenz"
    result["source_url"] = "https://data.sbb.ch/explore/dataset/passagierfrequenz/"
    return result


def json_bytes(value):
    return json.dumps(value, ensure_ascii=False, default=lambda item:float(item) if isinstance(item,Decimal) else str(item), allow_nan=False).encode()
