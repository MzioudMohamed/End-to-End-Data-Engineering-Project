import argparse
from datetime import datetime
from pathlib import Path

from delta import configure_spark_with_delta_pip
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, date_sub, lit
from pyspark.sql.types import DateType


parser = argparse.ArgumentParser(
    description="Applique les changements Customer au SCD2 existant."
)
parser.add_argument("--changes-path", required=True)
parser.add_argument("--change-date", required=True)
parser.add_argument(
    "--output-path",
    default="data/silver/customer",
)

args = parser.parse_args()

try:
    datetime.strptime(args.change_date, "%Y-%m-%d")
except ValueError as error:
    raise ValueError(
        "La date doit respecter le format AAAA-MM-JJ."
    ) from error

changes_path = Path(args.changes_path)

if not changes_path.is_file():
    raise FileNotFoundError(
        f"Fichier de changements introuvable : {changes_path}"
    )

output_path = Path(args.output_path)

if not output_path.exists():
    raise FileNotFoundError(
        "La table SCD2 existante est introuvable. "
        "Le chargement initial doit être réalisé avant le mode quotidien."
    )

spark_builder = (
    SparkSession.builder
    .appName("silver_customer_scd2_daily")
    .config(
        "spark.sql.extensions",
        "io.delta.sql.DeltaSparkSessionExtension",
    )
    .config(
        "spark.sql.catalog.spark_catalog",
        "org.apache.spark.sql.delta.catalog.DeltaCatalog",
    )
)

spark = configure_spark_with_delta_pip(spark_builder).getOrCreate()

try:
    existing = spark.read.format("delta").load(str(output_path))
    changes = spark.read.parquet(str(changes_path))

    required_columns = {
        "CustomerID",
        "CustomerName",
        "CustomerType",
        "TerritoryID",
    }

    missing_columns = required_columns.difference(changes.columns)

    if missing_columns:
        raise ValueError(
            f"Colonnes manquantes dans les changements : "
            f"{sorted(missing_columns)}"
        )

    changes = (
        changes
        .select(
            col("CustomerID").cast("long").alias("customer_id"),
            col("CustomerName").alias("customer_name"),
            col("CustomerType").alias("customer_type"),
            col("TerritoryID").cast("long").alias("territory_id"),
        )
        .withColumn(
            "change_date",
            lit(args.change_date).cast(DateType()),
        )
    )

    current = existing.filter(col("is_current"))

    comparison = (
        current.alias("old")
        .join(
            changes.alias("new"),
            col("old.customer_id") == col("new.customer_id"),
            "full",
        )
    )

    different_values = ~(
        col("old.customer_name").eqNullSafe(col("new.customer_name"))
        & col("old.customer_type").eqNullSafe(col("new.customer_type"))
        & col("old.territory_id").eqNullSafe(col("new.territory_id"))
    )

    changed_or_new = comparison.filter(
        col("new.customer_id").isNotNull()
        & (
            col("old.customer_id").isNull()
            | different_values
        )
    )

    changed_existing = changed_or_new.filter(
        col("old.customer_id").isNotNull()
    )

    changed_ids = changed_or_new.select(
        col("new.customer_id").alias("customer_id")
    ).distinct()

    historical = existing.filter(~col("is_current"))

    unchanged_current = (
        current
        .join(changed_ids, "customer_id", "left_anti")
    )

    unchanged_versions = historical.unionByName(unchanged_current)

    closed_versions = changed_existing.select(
        col("old.customer_id").alias("customer_id"),
        col("old.customer_name").alias("customer_name"),
        col("old.customer_type").alias("customer_type"),
        col("old.territory_id").alias("territory_id"),
        col("old.valid_from").alias("valid_from"),
        date_sub(
            col("new.change_date"),
            1,
        ).alias("valid_to"),
        lit(False).alias("is_current"),
        col("old.source_system").alias("source_system"),
    )

    new_versions = changed_or_new.select(
        col("new.customer_id").alias("customer_id"),
        col("new.customer_name").alias("customer_name"),
        col("new.customer_type").alias("customer_type"),
        col("new.territory_id").alias("territory_id"),
        col("new.change_date").alias("valid_from"),
        lit("9999-12-31").cast(DateType()).alias("valid_to"),
        lit(True).alias("is_current"),
        lit("adls_landing").alias("source_system"),
    )

    result = (
        unchanged_versions
        .unionByName(closed_versions)
        .unionByName(new_versions)
    )

    (
        result.write
        .format("delta")
        .mode("overwrite")
        .save(str(output_path))
    )

    print(f"Clients existants : {current.count()}")
    print(f"Changements reçus : {changes.count()}")
    print(f"Nouvelles versions : {new_versions.count()}")
    print(f"Lignes SCD2 finales : {result.count()}")
    print(f"Date appliquée : {args.change_date}")
    print(f"Destination : {output_path}")

finally:
    spark.stop()