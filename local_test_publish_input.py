from __future__ import annotations

import json
from datetime import datetime

from kafka import KafkaProducer

from config import INPUT_TOPIC, KAFKA_BOOTSTRAP


def build_input_message(job_id: str, index: int) -> dict:
    return {
        "job_id": job_id,
        "node_ip": f"10.20.0.{index}",
        "object_name": f"PON-1/0/{index}",
        "kpi_name": "octets_rx",
        "published_at": datetime.utcnow().isoformat() + "Z",
        "data": [
            {"ds": 1740000000000, "y": 4.1},
            {"ds": 1740003600000, "y": 4.7},
            {"ds": 1740007200000, "y": 5.0},
        ],
    }


def main() -> None:
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_serializer=lambda body: json.dumps(body).encode(),
    )
    job_id = "LOCAL-TEST-JOB-001"

    for i in range(1, 4):
        payload = build_input_message(job_id, i)
        headers = [
            ("job-id", job_id.encode()),
            ("node-ip", payload["node_ip"].encode()),
            ("object-name", payload["object_name"].encode()),
            ("kpi-name", payload["kpi_name"].encode()),
        ]
        key = f"{payload['node_ip']}:{payload['object_name']}".encode()
        producer.send(INPUT_TOPIC, key=key, value=payload, headers=headers)
        print(f"[LOCAL-TEST] Published input message #{i}")

    producer.flush()
    producer.close()
    print("[LOCAL-TEST] Done publishing input messages.")


if __name__ == "__main__":
    main()
