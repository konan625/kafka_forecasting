import json
import time
from datetime import datetime, timezone
from typing import Dict, List

from kafka import KafkaConsumer, KafkaProducer

from config import CONSUMER_GROUP_UFS, KAFKA_BOOTSTRAP, TOPIC_INPUT, TOPIC_OUTPUT


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def fake_token() -> str:
    return "Bearer local-dev-token-ufs"


def to_header_map(headers: List) -> Dict[str, str]:
    result = {}
    for k, v in headers:
        if isinstance(v, bytes):
            result[k] = v.decode(errors="ignore")
        else:
            result[k] = str(v)
    return result


def three_pass_forecast(data: List[Dict], horizon: int) -> List[Dict]:
    """
    Very small stand-in for your 3-pass pipeline.
    Returns same 4-segment layout:
    context2 + forecast2 + context3 + forecast3.
    """
    clean = [x for x in data if x["y"] is not None]
    if len(clean) < 3 * horizon:
        raise ValueError(f"Need at least {3*horizon} clean points, got {len(clean)}")

    context2 = clean[-2 * horizon : -horizon]
    context3 = clean[-horizon:]

    avg2 = sum(float(x["y"]) for x in context2) / len(context2)
    avg3 = sum(float(x["y"]) for x in context3) / len(context3)
    corrected = round((avg2 + avg3) / 2.0, 4)

    seg1 = [{"ds": x["ds"], "Actual": x["y"], "Forecast": None} for x in context2]
    seg2 = [{"ds": x["ds"], "Actual": None, "Forecast": corrected} for x in context3]
    future_start = context3[-1]["ds"] + 3600000
    seg4 = [
        {"ds": future_start + i * 3600000, "Actual": None, "Forecast": corrected}
        for i in range(horizon)
    ]
    seg3 = [{"ds": x["ds"], "Actual": x["y"], "Forecast": None} for x in context3]
    return seg1 + seg2 + seg3 + seg4


def main() -> None:
    consumer = KafkaConsumer(
        TOPIC_INPUT,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        group_id=CONSUMER_GROUP_UFS,
        enable_auto_commit=False,
        auto_offset_reset="earliest",
        max_poll_records=1,
        value_deserializer=lambda b: json.loads(b.decode()),
    )
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        acks="all",
        retries=3,
    )
    seen = set()

    print(f"[UFS] Listening on {TOPIC_INPUT} ...")
    for msg in consumer:
        started = time.time()
        body = msg.value
        h = to_header_map(msg.headers)

        idem = (
            f"{body['job_id']}:{body['batch_seq']}:"
            f"{body['node_ip']}:{body['object_name']}:{body['kpi_name']}"
        )
        if idem in seen:
            print(f"[UFS] Duplicate detected, committing offset only: {idem}")
            consumer.commit()
            continue

        try:
            horizon = int(body["forecast_params"]["horizon"])
            output_rows = three_pass_forecast(body["data"], horizon)
            processing_ms = int((time.time() - started) * 1000)
            result = {
                "job_id": body["job_id"],
                "batch_seq": body["batch_seq"],
                "total_batches": body["total_batches"],
                "node_ip": body["node_ip"],
                "object_name": body["object_name"],
                "kpi_name": body["kpi_name"],
                "status": "SUCCESS",
                "processed_at": utc_now(),
                "processing_ms": processing_ms,
                "model_calls": 3,
                "forecast_params": {
                    "horizon": body["forecast_params"]["horizon"],
                    "granularity_min": body["forecast_params"]["granularity_min"],
                    "aggregation": body["forecast_params"]["aggregation"],
                },
                "output": {"output": output_rows},
            }
            headers = [
                ("content-type", b"application/json"),
                ("schema-version", b"1.0"),
                ("source", b"ufs-forecast-worker"),
                ("job-id", body["job_id"].encode()),
                ("batch-seq", str(body["batch_seq"]).encode()),
                ("total-batches", str(body["total_batches"]).encode()),
                ("node-ip", body["node_ip"].encode()),
                ("object-name", body["object_name"].encode()),
                ("kpi-name", body["kpi_name"].encode()),
                ("status", b"SUCCESS"),
                ("authorization", fake_token().encode()),
                ("processing-ms", str(processing_ms).encode()),
            ]
        except Exception as e:
            processing_ms = int((time.time() - started) * 1000)
            result = {
                "job_id": body["job_id"],
                "batch_seq": body["batch_seq"],
                "total_batches": body["total_batches"],
                "node_ip": body["node_ip"],
                "object_name": body["object_name"],
                "kpi_name": body["kpi_name"],
                "status": "FAILED",
                "processed_at": utc_now(),
                "processing_ms": processing_ms,
                "model_calls": 1,
                "error": {
                    "code": "INSUFFICIENT_DATA",
                    "message": str(e),
                    "stage": "PREPROCESSING",
                },
                "output": None,
            }
            headers = [
                ("content-type", b"application/json"),
                ("schema-version", b"1.0"),
                ("source", b"ufs-forecast-worker"),
                ("job-id", body["job_id"].encode()),
                ("batch-seq", str(body["batch_seq"]).encode()),
                ("total-batches", str(body["total_batches"]).encode()),
                ("node-ip", body["node_ip"].encode()),
                ("object-name", body["object_name"].encode()),
                ("kpi-name", body["kpi_name"].encode()),
                ("status", b"FAILED"),
                ("authorization", fake_token().encode()),
                ("processing-ms", str(processing_ms).encode()),
            ]

        producer.send(
            TOPIC_OUTPUT,
            key=body["job_id"].encode(),
            value=json.dumps(result).encode(),
            headers=headers,
        )
        producer.flush()
        seen.add(idem)
        consumer.commit()  # commit only after output publish
        print(
            f"[UFS] Processed job={body['job_id']} batch={body['batch_seq']} "
            f"status={result['status']}"
        )


if __name__ == "__main__":
    main()
