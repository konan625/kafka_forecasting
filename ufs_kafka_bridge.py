from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any

from kafka import KafkaConsumer, KafkaProducer

from config import (
    CONSUMER_GROUP_ID,
    INPUT_TOPIC,
    KAFKA_BOOTSTRAP,
    MAX_POLL_RECORDS,
    OUTPUT_TOPIC,
)
from ufs_client import call_ufs_forecast


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_success_output(input_payload: dict, ufs_result: dict, processing_ms: int) -> dict:
    return {
        "job_id": input_payload.get("job_id"),
        "node_ip": input_payload.get("node_ip"),
        "object_name": input_payload.get("object_name"),
        "kpi_name": input_payload.get("kpi_name"),
        "status": "SUCCESS",
        "processed_at": now_utc_iso(),
        "processing_ms": processing_ms,
        "ufs_response": ufs_result,
    }


def build_failed_output(input_payload: dict, error_message: str, processing_ms: int) -> dict:
    return {
        "job_id": input_payload.get("job_id"),
        "node_ip": input_payload.get("node_ip"),
        "object_name": input_payload.get("object_name"),
        "kpi_name": input_payload.get("kpi_name"),
        "status": "FAILED",
        "processed_at": now_utc_iso(),
        "processing_ms": processing_ms,
        "error": {"message": error_message},
        "ufs_response": None,
    }


def read_headers_as_strings(headers: list[tuple[str, bytes]]) -> dict[str, str]:
    values: dict[str, str] = {}
    for key, value in headers:
        values[key] = value.decode() if isinstance(value, bytes) else str(value)
    return values


def build_output_headers(input_headers: dict[str, str], status: str, processing_ms: int) -> list[tuple[str, bytes]]:
    # Keep this intentionally small and readable.
    headers = [
        ("content-type", b"application/json"),
        ("source", b"ufs-kafka-bridge"),
        ("status", status.encode()),
        ("processing-ms", str(processing_ms).encode()),
    ]
    for name in ("job-id", "node-ip", "object-name", "kpi-name"):
        if name in input_headers:
            headers.append((name, input_headers[name].encode()))
    return headers


def main() -> None:
    consumer = KafkaConsumer(
        INPUT_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        group_id=CONSUMER_GROUP_ID,
        enable_auto_commit=False,
        auto_offset_reset="earliest",
        max_poll_records=MAX_POLL_RECORDS,
        value_deserializer=lambda raw: json.loads(raw.decode()),
    )

    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        acks="all",
        retries=5,
        value_serializer=lambda body: json.dumps(body).encode(),
    )

    print(f"[UFS-BRIDGE] Started. Input={INPUT_TOPIC}, Output={OUTPUT_TOPIC}, Bootstrap={KAFKA_BOOTSTRAP}")
    print("[UFS-BRIDGE] Waiting for messages... (processes sequentially)")

    for message in consumer:
        started = time.time()
        input_payload: dict[str, Any] = message.value
        input_headers = read_headers_as_strings(message.headers)

        try:
            ufs_result = call_ufs_forecast(input_payload)
            processing_ms = int((time.time() - started) * 1000)
            output_payload = build_success_output(input_payload, ufs_result, processing_ms)
            status = "SUCCESS"
        except Exception as exc:  # Keep broad for minimal learning project.
            processing_ms = int((time.time() - started) * 1000)
            output_payload = build_failed_output(input_payload, str(exc), processing_ms)
            status = "FAILED"

        output_headers = build_output_headers(input_headers, status, processing_ms)
        output_key = str(input_payload.get("job_id", "unknown-job")).encode()

        producer.send(
            OUTPUT_TOPIC,
            key=output_key,
            value=output_payload,
            headers=output_headers,
        )
        producer.flush()
        consumer.commit()  # Commit only after result is published.

        print(
            "[UFS-BRIDGE] Processed message "
            f"partition={message.partition}, offset={message.offset}, status={status}"
        )


if __name__ == "__main__":
    main()
