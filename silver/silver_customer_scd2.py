from delta import configure_spark_with_delta_pip
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lit, when
from pyspark.sql.types import DateType


spark_builder = (
    SparkSession.builder
    .appName("silver_customer_scd2")
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

j0_path = "data/landing/customer/customer_j0.parquet"
changes_path = "data/landing/customer/customer_2014-05-01.parquet"
output_path = "data/silver/customer"

try:
    j0 = spark.read.parquet(j0_path)
    changes = spark.read.parquet(changes_path)

    j0 = (
        j0
        .select(
            col("CustomerID").cast("long").alias("customer_id"),
            col("CustomerName").alias("customer_name"),
            col("CustomerType").alias("customer_type"),
            col("TerritoryID").cast("long").alias("territory_id"),
        )
        .withColumn("valid_from", lit("2011-05-31").cast(DateType()))
        .withColumn("valid_to", lit("9999-12-31").cast(DateType()))
        .withColumn("is_current", lit(True))
    )

    changes = (
        changes
        .select(
            col("CustomerID").cast("long").alias("customer_id"),
            col("CustomerName").alias("customer_name"),
            col("CustomerType").alias("customer_type"),
            col("TerritoryID").cast("long").alias("territory_id"),
        )
        .withColumn("change_date", lit("2014-05-01").cast(DateType()))
    )

    comparison = (
        j0.alias("old")
        .join(changes.alias("new"), "customer_id", "full")
    )

    unchanged = (
        comparison
        .filter(
            col("new.customer_id").isNull()
            | (
                (col("old.customer_name") == col("new.customer_name"))
                & (col("old.customer_type") == col("new.customer_type"))
                & (col("old.territory_id") == col("new.territory_id"))
            )
        )
        .select(
            col("old.customer_id").alias("customer_id"),
            col("old.customer_name").alias("customer_name"),
            col("old.customer_type").alias("customer_type"),
            col("old.territory_id").alias("territory_id"),
            col("old.valid_from").alias("valid_from"),
            col("old.valid_to").alias("valid_to"),
            col("old.is_current").alias("is_current"),
        )
    )

    closed_versions = (
        comparison
        .filter(
            col("old.customer_id").isNotNull()
            & col("new.customer_id").isNotNull()
            & (
                (col("old.customer_name") != col("new.customer_name"))
                | (col("old.customer_type") != col("new.customer_type"))
                | (col("old.territory_id") != col("new.territory_id"))
            )
        )
        .select(
            col("old.customer_id").alias("customer_id"),
            col("old.customer_name").alias("customer_name"),
            col("old.customer_type").alias("customer_type"),
            col("old.territory_id").alias("territory_id"),
            col("old.valid_from").alias("valid_from"),
            (col("new.change_date") - 1).alias("valid_to"),
            lit(False).alias("is_current"),
        )
    )

    new_versions = (
        changes
        .select(
            col("customer_id"),
            col("customer_name"),
            col("customer_type"),
            col("territory_id"),
            col("change_date").alias("valid_from"),
            lit("9999-12-31").cast(DateType()).alias("valid_to"),
            lit(True).alias("is_current"),
        )
    )

    silver_customer = (
        unchanged
        .unionByName(closed_versions)
        .unionByName(new_versions)
        .withColumn("source_system", lit("adls_landing"))
    )

    (
        silver_customer.write
        .format("delta")
        .mode("overwrite")
        .save(output_path)
    )

    print(f"Clients J0 : {j0.count()}")
    print(f"Lignes de changement : {changes.count()}")
    print(f"Lignes Silver SCD2 : {silver_customer.count()}")
    print(f"Destination : {output_path}")

finally:
    spark.stop()