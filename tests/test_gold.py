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

    raise EnvironmentError("Java est introuvable pour exécuter les tests Gold.")


@pytest.fixture(scope="session")
def spark():
    configure_java_home()

    builder = (
        SparkSession.builder
        .appName("test_gold")
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
def gold_tables(spark):
    paths = {
        "customer": Path("data/gold/dim_customer"),
        "date": Path("data/gold/dim_date"),
        "territory": Path("data/gold/dim_territory"),
        "sales": Path("data/gold/fact_sales"),
    }

    missing_paths = [
        str(path) for path in paths.values() if not path.exists()
    ]

    if missing_paths:
        pytest.fail(f"Tables Gold introuvables : {missing_paths}")

    return {
        name: spark.read.format("delta").load(str(path))
        for name, path in paths.items()
    }


def test_gold_tables_are_not_empty(gold_tables):
    for name, table in gold_tables.items():
        assert table.count() > 0, f"Table Gold vide : {name}"


def test_fact_sales_has_no_missing_customer_key(gold_tables):
    missing_keys = gold_tables["sales"].filter(
        col("customer_sk").isNull()
    ).count()

    assert missing_keys == 0


def test_fact_sales_has_no_duplicate_order_id(gold_tables):
    duplicate_orders = (
        gold_tables["sales"]
        .groupBy("sales_order_id")
        .count()
        .filter(col("count") > 1)
        .count()
    )

    assert duplicate_orders == 0


def test_fact_sales_has_no_missing_date_key(gold_tables):
    missing_dates = gold_tables["sales"].filter(
        col("date_key").isNull()
    ).count()

    assert missing_dates == 0