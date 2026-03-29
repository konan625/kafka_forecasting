from kafka import KafkaAdminClient
from kafka.admin import NewTopic
from kafka.errors import TopicAlreadyExistsError

from config import (
    INPUT_PARTITIONS,
    KAFKA_BOOTSTRAP,
    OUTPUT_PARTITIONS,
    TOPIC_INPUT,
    TOPIC_OUTPUT,
)


def main() -> None:
    admin = KafkaAdminClient(bootstrap_servers=KAFKA_BOOTSTRAP, client_id="ufs-admin")
    topics = [
        NewTopic(name=TOPIC_INPUT, num_partitions=INPUT_PARTITIONS, replication_factor=1),
        NewTopic(name=TOPIC_OUTPUT, num_partitions=OUTPUT_PARTITIONS, replication_factor=1),
    ]
    for topic in topics:
        try:
            admin.create_topics([topic])
            print(f"Created topic: {topic.name}")
        except TopicAlreadyExistsError:
            print(f"Topic already exists: {topic.name}")
    admin.close()


if __name__ == "__main__":
    main()
