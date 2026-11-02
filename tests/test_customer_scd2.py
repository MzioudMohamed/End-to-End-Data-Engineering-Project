import os
import shutil
from pathlib import Path

import pytest
from delta import configure_spark_with_delta_pip
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lit


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

    raise EnvironmentError(
        "Java est introuvable pour exécuter le test SCD2."
    )


@pytest.fixture(scope="session")
def spark():
    configure_java_home()

    builder = (
        SparkSession.builder
        .appName("test_customer_scd2")
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
def customer_table(spark):
    table_path = Path("data/silver/customer")

    if not table_path.exists():
        pytest.fail(f"Table SCD2 introuvable : {table_path}")

    return spark.read.format("delta").load(str(table_path))


def test_customer_table_is_not_empty(customer_table):
    assert customer_table.count() > 0


def test_each_customer_has_one_current_version(customer_table):
    duplicated_current_versions = (
        customer_table
        .filter(col("is_current"))
        .groupBy("customer_id")
        .count()
        .filter(col("count") > 1)
        .count()
    )

    assert duplicated_current_versions == 0


def test_scd2_periods_are_valid(customer_table):
    invalid_periods = customer_table.filter(
        col("valid_to") < col("valid_from")
    ).count()

    assert invalid_periods == 0


def test_current_versions_have_open_end_date(customer_table):
    invalid_current_versions = customer_table.filter(
        col("is_current")
        & (
            col("valid_to")
            != lit("9999-12-31").cast("date")
        )
    ).count()

    assert invalid_current_versions == 0