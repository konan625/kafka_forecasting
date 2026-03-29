KAFKA_BOOTSTRAP = "localhost:9092"

TOPIC_INPUT = "ufs.bulk.input"
TOPIC_OUTPUT = "ufs.bulk.output"

INPUT_PARTITIONS = 6
OUTPUT_PARTITIONS = 6

ROW_COUNT_THRESHOLD = 50000

CONSUMER_GROUP_UFS = "ufs-bulk-forecast-workers"
CONSUMER_GROUP_RT = "report-tool-consumer"
