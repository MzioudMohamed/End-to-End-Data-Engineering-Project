import os
import shutil
import sys
from pathlib import Path


def configure_java_home() -> None:
    """Configure JAVA_HOME for PySpark when Windows only exposes java on PATH."""
    configured_home = os.environ.get("JAVA_HOME")
    if configured_home:
        configured_binary = Path(configured_home) / "bin" / "java.exe"
        if configured_binary.is_file():
            return

    java_executable = shutil.which("java")
    candidates = []

    if java_executable is not None:
        candidates.append(Path(java_executable).resolve().parent.parent)

    program_files = os.environ.get("ProgramFiles")
    if program_files:
        program_files_path = Path(program_files)
        candidates.extend(program_files_path.glob("Java/*"))
        candidates.extend(program_files_path.glob("Eclipse Adoptium/*"))
        candidates.extend(program_files_path.glob("Microsoft/*"))
        candidates.extend(program_files_path.glob("Amazon Corretto/*"))

    for java_home in candidates:
        if (java_home / "bin" / "java.exe").is_file():
            os.environ["JAVA_HOME"] = str(java_home)
            return

    raise EnvironmentError(
        "Java est introuvable. Installez Java 11 ou 17 et définissez JAVA_HOME "
        "vers le dossier qui contient bin\\java.exe."
    )


configure_java_home()

from delta import configure_spark_with_delta_pip
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, current_timestamp
from pyspark.sql.types import DecimalType


input_path = Path("data/bronze/salesorderheader")
output_path = "data/silver/salesorderheader"


if not input_path.exists():
    raise FileNotFoundError(f"Table Bronze introuvable : {input_path}")


builder = (
    SparkSession.builder
    .appName("silver_salesorderheader")
    .config(
        "spark.sql.extensions",
        "io.delta.sql.DeltaSparkSessionExtension",
    )
    .config(
        "spark.sql.catalog.spark_catalog",
        "org.apache.spark.sql.delta.catalog.DeltaCatalog",
    )
)

spark = configure_spark_with_delta_pip(builder).getOrCreate()

try:
    bronze = spark.read.format("delta").load(str(input_path))

    required_columns = {
        "SalesOrderID",
        "OrderDate",
        "CustomerID",
        "TerritoryID",
        "OnlineOrderFlag",
        "SubTotal",
        "TaxAmt",
        "Freight",
        "load_date",
        "source_system",
        "ingestion_timestamp",
    }

    missing_columns = required_columns.difference(bronze.columns)

    if missing_columns:
        raise ValueError(
            f"Colonnes Bronze manquantes : {sorted(missing_columns)}"
        )

    null_key_count = (
        bronze
        .filter(
            col("SalesOrderID").isNull()
            | col("OrderDate").isNull()
            | col("CustomerID").isNull()
        )
        .count()
    )

    if null_key_count > 0:
        raise ValueError(
            f"{null_key_count} ligne(s) ont une clé obligatoire nulle."
        )

    duplicate_key_count = (
        bronze
        .groupBy("SalesOrderID")
        .count()
        .filter(col("count") > 1)
        .count()
    )

    if duplicate_key_count > 0:
        raise ValueError(
            f"{duplicate_key_count} SalesOrderID dupliqué(s) détecté(s)."
        )

    silver = (
        bronze
        .select(
            col("SalesOrderID").cast("long").alias("sales_order_id"),
            col("OrderDate").cast("date").alias("order_date"),
            col("CustomerID").cast("long").alias("customer_id"),
            col("TerritoryID").cast("long").alias("territory_id"),
            col("OnlineOrderFlag").cast("boolean").alias("is_online_order"),
            col("SubTotal")
            .cast(DecimalType(19, 4))
            .alias("subtotal_amount"),
            col("TaxAmt")
            .cast(DecimalType(19, 4))
            .alias("tax_amount"),
            col("Freight")
            .cast(DecimalType(19, 4))
            .alias("freight_amount"),
            col("load_date").cast("date").alias("load_date"),
            col("source_system"),
            col("ingestion_timestamp"),
        )
        .withColumn("silver_processed_timestamp", current_timestamp())
    )

    (
        silver.write
        .format("delta")
        .mode("overwrite")
        .partitionBy("load_date")
        .save(output_path)
    )

    print(f"Lignes chargées en Silver : {silver.count()}")
    print(f"Destination : {output_path}")

finally:
    spark.stop()