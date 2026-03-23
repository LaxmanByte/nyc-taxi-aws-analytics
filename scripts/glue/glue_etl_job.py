# =============================================================
# AWS Glue ETL Job - NYC Taxi Analytics Pipeline
# Author: Laxman Barre
# Description: Transforms raw NYC taxi Parquet data from S3,
#              cleans and enriches it, then loads to Redshift
# =============================================================

import sys
import logging
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, IntegerType, TimestampType

# ----- Setup Logging -----
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ----- Job Parameters -----
args = getResolvedOptions(sys.argv, [
    'JOB_NAME',
    'SOURCE_BUCKET',
    'TARGET_BUCKET',
    'REDSHIFT_CONNECTION',
    'REDSHIFT_DB',
    'REDSHIFT_TABLE'
])

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

logger.info("Starting NYC Taxi ETL Job...")

# ----- Step 1: Read Raw Data from S3 (Parquet) -----
logger.info(f"Reading raw data from s3://{args['SOURCE_BUCKET']}/raw/")

raw_df = spark.read.parquet(f"s3://{args['SOURCE_BUCKET']}/raw/")

logger.info(f"Raw records loaded: {raw_df.count()}")
logger.info(f"Schema: {raw_df.printSchema()}")

# ----- Step 2: Data Cleaning & Transformation -----
logger.info("Applying data cleaning and transformations...")

cleaned_df = raw_df \
    .filter(F.col('tpep_pickup_datetime').isNotNull()) \
    .filter(F.col('tpep_dropoff_datetime').isNotNull()) \
    .filter(F.col('trip_distance') > 0) \
    .filter(F.col('fare_amount') > 0) \
    .filter(F.col('passenger_count') > 0) \
    .filter(F.col('passenger_count') <= 6) \
    .dropDuplicates()

# ----- Step 3: Feature Engineering -----
logger.info("Adding derived columns...")

enriched_df = cleaned_df \
    .withColumn('trip_duration_minutes',
        (F.unix_timestamp('tpep_dropoff_datetime') -
         F.unix_timestamp('tpep_pickup_datetime')) / 60
    ) \
    .withColumn('pickup_hour', F.hour('tpep_pickup_datetime')) \
    .withColumn('pickup_day', F.dayofweek('tpep_pickup_datetime')) \
    .withColumn('pickup_date', F.to_date('tpep_pickup_datetime')) \
    .withColumn('pickup_month', F.month('tpep_pickup_datetime')) \
    .withColumn('pickup_year', F.year('tpep_pickup_datetime')) \
    .withColumn('revenue_per_mile',
        F.when(F.col('trip_distance') > 0,
               F.round(F.col('total_amount') / F.col('trip_distance'), 2)
        ).otherwise(0)
    ) \
    .withColumn('payment_type_desc',
        F.when(F.col('payment_type') == 1, 'Credit Card')
         .when(F.col('payment_type') == 2, 'Cash')
         .when(F.col('payment_type') == 3, 'No Charge')
         .when(F.col('payment_type') == 4, 'Dispute')
         .otherwise('Unknown')
    ) \
    .filter(F.col('trip_duration_minutes') > 0) \
    .filter(F.col('trip_duration_minutes') < 300)

logger.info(f"Cleaned and enriched records: {enriched_df.count()}")

# ----- Step 4: Write Processed Data to S3 (Parquet) -----
logger.info(f"Writing processed data to s3://{args['TARGET_BUCKET']}/processed/")

enriched_df.write \
    .mode('overwrite') \
    .partitionBy('pickup_year', 'pickup_month') \
    .parquet(f"s3://{args['TARGET_BUCKET']}/processed/")

logger.info("Processed data written to S3 successfully.")

# ----- Step 5: Write to Redshift Serverless -----
logger.info(f"Loading data into Redshift table: {args['REDSHIFT_TABLE']}")

glueContext.write_dynamic_frame.from_jdbc_conf(
    frame=DynamicFrame.fromDF(enriched_df, glueContext, 'enriched_df'),
    catalog_connection=args['REDSHIFT_CONNECTION'],
    connection_options={
        'dbtable': args['REDSHIFT_TABLE'],
        'database': args['REDSHIFT_DB'],
        'preactions': f"TRUNCATE TABLE {args['REDSHIFT_TABLE']};"
    },
    redshift_tmp_dir=f"s3://{args['TARGET_BUCKET']}/redshift-temp/"
)

logger.info("Data loaded to Redshift successfully.")
logger.info("NYC Taxi ETL Job completed successfully!")

job.commit()
