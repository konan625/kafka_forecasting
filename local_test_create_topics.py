from __future__ import annotations

from kafka import KafkaAdminClient
from kafka.admin import NewTopic
from kafka.errors import TopicAlreadyExistsError

from config import INPUT_TOPIC, KAFKA_BOOTSTRAP, OUTPUT_TOPIC


def create_topic_if_missing(admin: KafkaAdminClient, topic_name: str, partitions: int = 3) -> None:
    try:
        admin.create_topics(
            [NewTopic(name=topic_name, num_partitions=partitions, replication_factor=1)]
        )
        print(f"[LOCAL-TEST] Created topic: {topic_name}")
    except TopicAlreadyExistsError:
        print(f"[LOCAL-TEST] Topic already exists: {topic_name}")


def main() -> None:
    admin = KafkaAdminClient(bootstrap_servers=KAFKA_BOOTSTRAP, client_id="ufs-local-test")
    create_topic_if_missing(admin, INPUT_TOPIC)
    create_topic_if_missing(admin, OUTPUT_TOPIC)
    admin.close()


if __name__ == "__main__":
    main()
