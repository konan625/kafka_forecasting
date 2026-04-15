from __future__ import annotations

import json

from kafka import KafkaConsumer

from config import KAFKA_BOOTSTRAP, OUTPUT_TOPIC


def main() -> None:
    consumer = KafkaConsumer(
        OUTPUT_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        group_id="ufs-local-output-reader",
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        value_deserializer=lambda raw: json.loads(raw.decode()),
    )
    print(f"[LOCAL-TEST] Reading output from topic={OUTPUT_TOPIC}")
    print("[LOCAL-TEST] Press Ctrl+C to stop.\n")

    for message in consumer:
        payload = message.value
        print(
            "[LOCAL-TEST][OUTPUT] "
            f"partition={message.partition} offset={message.offset} "
            f"status={payload.get('status')} "
            f"job_id={payload.get('job_id')} "
            f"node={payload.get('node_ip')} "
            f"object={payload.get('object_name')} "
            f"kpi={payload.get('kpi_name')}"
        )
        print(json.dumps(payload, indent=2))
        print("-" * 80)


if __name__ == "__main__":
    main()
