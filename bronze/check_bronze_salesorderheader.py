from delta import configure_spark_with_delta_pip
from pyspark.sql import SparkSession
from pyspark.sql.functions import col


builder = (
    SparkSession.builder
    .appName("check_bronze_salesorderheader")
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
    table = spark.read.format("delta").load("data/bronze/salesorderheader")

    total_rows = table.count()
    null_ids = table.filter(col("SalesOrderID").isNull()).count()
    duplicate_ids = (
        table.groupBy("SalesOrderID")
        .count()
        .filter(col("count") > 1)
        .count()
    )

    required_columns = {
        "load_date",
        "source_system",
        "ingestion_timestamp",
    }

    missing_columns = required_columns.difference(table.columns)

    print(f"Total de lignes : {total_rows}")
    print(f"SalesOrderID nuls : {null_ids}")
    print(f"Groupes dupliqués : {duplicate_ids}")
    print(f"Colonnes d'audit manquantes : {sorted(missing_columns)}")

    if total_rows == 0:
        raise ValueError("La table Bronze est vide.")

    if null_ids > 0:
        raise ValueError("Des SalesOrderID sont nuls.")

    if duplicate_ids > 0:
        raise ValueError("Des SalesOrderID sont dupliqués.")

    if missing_columns:
        raise ValueError("Des colonnes d'audit sont absentes.")

    print("Contrôles Bronze réussis.")
finally:
    spark.stop()