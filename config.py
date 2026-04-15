import os

# Kafka connection settings. Report Tool owns topic creation/config.
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
INPUT_TOPIC = os.getenv("INPUT_TOPIC", "ufs.bulk.input")
OUTPUT_TOPIC = os.getenv("OUTPUT_TOPIC", "ufs.bulk.output")
CONSUMER_GROUP_ID = os.getenv("CONSUMER_GROUP_ID", "ufs-service-non-batch")

# UFS endpoint for forecast execution.
# Replace with office endpoint when deployed.
UFS_FORECAST_ENDPOINT = os.getenv("UFS_FORECAST_ENDPOINT", "https://xyz.something/forecast")
UFS_TIMEOUT_SECONDS = int(os.getenv("UFS_TIMEOUT_SECONDS", "30"))

# Processing style: one message at a time in receive order.
MAX_POLL_RECORDS = int(os.getenv("MAX_POLL_RECORDS", "1"))
