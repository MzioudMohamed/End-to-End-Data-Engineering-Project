from delta import configure_spark_with_delta_pip
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col,
    explode,
    lit,
    max,
    min,
    quarter,
    row_number,
    sequence,
    year,
)
from pyspark.sql.window import Window


spark_builder = (
    SparkSession.builder
    .appName("gold_sales")
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

sales_path = "data/silver/salesorderheader"
customer_path = "data/silver/customer"
gold_path = "data/gold"

try:
    sales = spark.read.format("delta").load(sales_path)
    customers = spark.read.format("delta").load(customer_path)

    customer_window = Window.orderBy("customer_id", "valid_from")

    dim_customer = (
        customers
        .withColumn("customer_sk", row_number().over(customer_window))
        .select(
            "customer_sk",
            "customer_id",
            "customer_name",
            "customer_type",
            "territory_id",
            "valid_from",
            "valid_to",
            "is_current",
            "source_system",
        )
    )

    date_range = sales.select(
        min("order_date").alias("first_date"),
        max("order_date").alias("last_date"),
    ).first()

    dim_date = (
        spark.range(1)
        .select(
            explode(
                sequence(
                    lit(date_range["first_date"]),
                    lit(date_range["last_date"]),
                )
            ).alias("date")
        )
        .select(
            col("date").alias("date_key"),
            year("date").alias("year"),
            quarter("date").alias("quarter"),
        )
    )

    dim_territory = (
        sales
        .select("territory_id")
        .where(col("territory_id").isNotNull())
        .distinct()
        .withColumn(
            "territory_sk",
            row_number().over(Window.orderBy("territory_id")),
        )
        .select("territory_sk", "territory_id")
    )

    fact_sales = (
        sales.alias("sales")
        .join(
            dim_customer.alias("customer"),
            (col("sales.customer_id") == col("customer.customer_id"))
            & (
                col("sales.order_date").between(
                    col("customer.valid_from"),
                    col("customer.valid_to"),
                )
            ),
            "left",
        )
        .select(
            col("sales.sales_order_id"),
            col("sales.order_date").alias("date_key"),
            col("customer.customer_sk"),
            col("sales.territory_id"),
            col("sales.is_online_order"),
            col("sales.subtotal_amount"),
            col("sales.tax_amount"),
            col("sales.freight_amount"),
            col("sales.load_date"),
            col("sales.source_system"),
            col("sales.silver_processed_timestamp"),
        )
    )

    (
        dim_customer.write
        .format("delta")
        .mode("overwrite")
        .save(f"{gold_path}/dim_customer")
    )

    (
        dim_date.write
        .format("delta")
        .mode("overwrite")
        .save(f"{gold_path}/dim_date")
    )

    (
        dim_territory.write
        .format("delta")
        .mode("overwrite")
        .save(f"{gold_path}/dim_territory")
    )

    (
        fact_sales.write
        .format("delta")
        .mode("overwrite")
        .partitionBy("date_key")
        .save(f"{gold_path}/fact_sales")
    )

    print(f"dim_customer : {dim_customer.count()}")
    print(f"dim_date : {dim_date.count()}")
    print(f"dim_territory : {dim_territory.count()}")
    print(f"fact_sales : {fact_sales.count()}")

finally:
    spark.stop()