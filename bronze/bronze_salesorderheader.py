import sys
from pathlib import Path

from delta import configure_spark_with_delta_pip
from pyspark.sql import SparkSession
from pyspark.sql.functions import current_timestamp, lit


if len(sys.argv) != 3:
    raise SystemExit(
        "Usage : python bronze_salesorderheader.py <fichier_parquet> <load_date>"
    )

input_path = Path(sys.argv[1])
load_date = sys.argv[2]
output_path = "data/bronze/salesorderheader"

if not input_path.is_file():
    raise FileNotFoundError(f"Fichier introuvable : {input_path}")


builder = (
    SparkSession.builder
    .appName("bronze_salesorderheader")
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
    sales_order_header = spark.read.parquet(str(input_path))

    bronze_sales_order_header = (
        sales_order_header
        .withColumn("load_date", lit(load_date))
        .withColumn("source_system", lit("adls_landing"))
        .withColumn("ingestion_timestamp", current_timestamp())
    )

    (
        bronze_sales_order_header.write
        .format("delta")
        .mode("overwrite")
        .option("replaceWhere", f"load_date = '{load_date}'")
        .partitionBy("load_date")
        .save(output_path)
    )

    print(f"Lignes chargées en Bronze : {bronze_sales_order_header.count()}")
    print(f"Date de chargement : {load_date}")
    print(f"Destination : {output_path}")
finally:
    spark.stop()