from delta import configure_spark_with_delta_pip
from pyspark.sql import SparkSession
from pyspark.sql.functions import col


builder = (
    SparkSession.builder
    .appName("check_gold_sales")
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
    customer = spark.read.format("delta").load("data/gold/dim_customer")
    date = spark.read.format("delta").load("data/gold/dim_date")
    territory = spark.read.format("delta").load("data/gold/dim_territory")
    sales = spark.read.format("delta").load("data/gold/fact_sales")

    missing_customer_keys = sales.filter(
        col("customer_sk").isNull()
    ).count()

    duplicate_sales = (
        sales.groupBy("sales_order_id")
        .count()
        .filter(col("count") > 1)
        .count()
    )

    missing_date_keys = sales.filter(
        col("date_key").isNull()
    ).count()

    print(f"dim_customer : {customer.count()}")
    print(f"dim_date : {date.count()}")
    print(f"dim_territory : {territory.count()}")
    print(f"fact_sales : {sales.count()}")
    print(f"Faits sans customer_sk : {missing_customer_keys}")
    print(f"Faits dupliqués : {duplicate_sales}")
    print(f"Faits sans date_key : {missing_date_keys}")

    if missing_customer_keys > 0:
        raise ValueError("Des faits ne trouvent pas de version Customer.")

    if duplicate_sales > 0:
        raise ValueError("Des SalesOrderID sont dupliqués dans la fact.")

    if missing_date_keys > 0:
        raise ValueError("Des faits n'ont pas de date.")

    print("Contrôles Gold réussis.")

finally:
    spark.stop()