import os
import shutil
from pathlib import Path

from delta import configure_spark_with_delta_pip
from pyspark.sql import SparkSession
from pyspark.sql.functions import col


def configure_java_home() -> None:
    configured_home = os.environ.get("JAVA_HOME")

    if configured_home:
        java_path = Path(configured_home) / "bin" / "java.exe"
        if java_path.is_file():
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

table_path = "data/silver/salesorderheader"

builder = (
    SparkSession.builder
    .appName("check_silver_salesorderheader")
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
    table = spark.read.format("delta").load(table_path)

    required_columns = {
        "sales_order_id",
        "order_date",
        "customer_id",
        "territory_id",
        "is_online_order",
        "subtotal_amount",
        "tax_amount",
        "freight_amount",
        "load_date",
        "source_system",
        "ingestion_timestamp",
        "silver_processed_timestamp",
    }

    missing_columns = required_columns.difference(table.columns)

    if missing_columns:
        raise ValueError(
            f"Colonnes Silver manquantes : {sorted(missing_columns)}"
        )

    total_rows = table.count()

    null_key_rows = (
        table
        .filter(
            col("sales_order_id").isNull()
            | col("order_date").isNull()
            | col("customer_id").isNull()
        )
        .count()
    )

    duplicate_key_groups = (
        table
        .groupBy("sales_order_id")
        .count()
        .filter(col("count") > 1)
        .count()
    )

    invalid_amount_rows = (
        table
        .filter(
            (col("subtotal_amount") < 0)
            | (col("tax_amount") < 0)
            | (col("freight_amount") < 0)
        )
        .count()
    )

    null_load_dates = table.filter(col("load_date").isNull()).count()
    null_sources = table.filter(col("source_system").isNull()).count()

    print(f"Total de lignes : {total_rows}")
    print(f"Lignes avec clé obligatoire nulle : {null_key_rows}")
    print(f"Groupes de SalesOrderID dupliqués : {duplicate_key_groups}")
    print(f"Lignes avec montant négatif : {invalid_amount_rows}")
    print(f"Lignes avec load_date nul : {null_load_dates}")
    print(f"Lignes avec source_system nul : {null_sources}")

    if total_rows == 0:
        raise ValueError("La table Silver est vide.")

    if null_key_rows > 0:
        raise ValueError("Des clés obligatoires sont nulles.")

    if duplicate_key_groups > 0:
        raise ValueError("Des SalesOrderID sont dupliqués.")

    if invalid_amount_rows > 0:
        raise ValueError("Des montants négatifs sont présents.")

    if null_load_dates > 0:
        raise ValueError("Des load_date sont nulles.")

    if null_sources > 0:
        raise ValueError("Des source_system sont nulles.")

    print("Contrôles Silver réussis.")

finally:
    spark.stop()