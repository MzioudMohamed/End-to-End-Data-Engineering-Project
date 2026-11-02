import os
import shutil
from pathlib import Path

import pytest
from delta import configure_spark_with_delta_pip
from pyspark.sql import SparkSession
from pyspark.sql.functions import col


def configure_java_home() -> None:
    configured_home = os.environ.get("JAVA_HOME")

    if configured_home:
        if (Path(configured_home) / "bin" / "java.exe").is_file():
            return

    java_executable = shutil.which("java")

    if java_executable is not None:
        java_home = Path(java_executable).resolve().parent.parent

        if (java_home / "bin" / "java.exe").is_file():
            os.environ["JAVA_HOME"] = str(java_home)
            return

    raise EnvironmentError("Java est introuvable.")


@pytest.fixture(scope="session")
def spark():
    configure_java_home()

    builder = (
        SparkSession.builder
        .appName("test_bronze_silver")
        .master("local[2]")
        .config(
            "spark.sql.extensions",
            "io.delta.sql.DeltaSparkSessionExtension",
        )
        .config(
            "spark.sql.catalog.spark_catalog",
            "org.apache.spark.sql.delta.catalog.DeltaCatalog",
        )
    )

    session = configure_spark_with_delta_pip(builder).getOrCreate()
    yield session
    session.stop()


@pytest.fixture(scope="session")
def bronze(spark):
    path = Path("data/bronze/salesorderheader")

    if not path.exists():
        pytest.fail(f"Table Bronze introuvable : {path}")

    return spark.read.format("delta").load(str(path))


@pytest.fixture(scope="session")
def silver(spark):
    path = Path("data/silver/salesorderheader")

    if not path.exists():
        pytest.fail(f"Table Silver introuvable : {path}")

    return spark.read.format("delta").load(str(path))


def test_bronze_is_not_empty(bronze):
    assert bronze.count() > 0


def test_bronze_has_unique_order_ids(bronze):
    duplicate_orders = (
        bronze.groupBy("SalesOrderID")
        .count()
        .filter(col("count") > 1)
        .count()
    )

    assert duplicate_orders == 0


def test_bronze_has_audit_columns(bronze):
    required_columns = {
        "load_date",
        "source_system",
        "ingestion_timestamp",
    }

    assert required_columns.issubset(set(bronze.columns))


def test_silver_is_not_empty(silver):
    assert silver.count() > 0


def test_silver_has_unique_order_ids(silver):
    duplicate_orders = (
        silver.groupBy("sales_order_id")
        .count()
        .filter(col("count") > 1)
        .count()
    )

    assert duplicate_orders == 0


def test_silver_has_no_invalid_amounts(silver):
    invalid_amounts = silver.filter(
        (col("subtotal_amount") < 0)
        | (col("tax_amount") < 0)
        | (col("freight_amount") < 0)
    ).count()

    assert invalid_amounts == 0