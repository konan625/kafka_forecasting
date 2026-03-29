import json
import random
from datetime import datetime, timezone
from typing import Dict, List, Tuple

from kafka import KafkaProducer

from config import KAFKA_BOOTSTRAP, ROW_COUNT_THRESHOLD, TOPIC_INPUT


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def fake_token() -> str:
    return "Bearer local-dev-token"


def make_series(points: int) -> List[Dict]:
    base_ts = 1740000000000
    rows = []
    for i in range(points):
        y = round(random.uniform(1.0, 10.0), 4)
        # inject small missing data pattern
        if i % 97 == 0:
            y = None
        rows.append({"ds": base_ts + i * 3600000, "y": y})
    return rows


def build_batch(
    job_id: str,
    batch_seq: int,
    total_batches: int,
    node_ip: str,
    object_name: str,
    kpi_name: str,
    points: int = 120,
) -> Tuple[bytes, List[Tuple[str, bytes]], str]:
    payload = {
        "job_id": job_id,
        "batch_seq": batch_seq,
        "total_batches": total_batches,
        "published_at": utc_now(),
        "node_ip": node_ip,
        "object_name": object_name,
        "kpi_name": kpi_name,
        "forecast_params": {
            "horizon": 24,
            "granularity_min": 60,
            "aggregation": "AVG",
            "daily_seasonality": False,
            "weekly_seasonality": True,
            "yearly_seasonality": False,
            "confidence_interval": 0.95,
        },
        "data": make_series(points),
        "data_quality": {
            "total_points": points,
            "missing_points": points // 97,
            "missing_pct": round((points // 97) * 100.0 / points, 2),
            "has_large_gaps": False,
        },
    }
    partition_key = f"{node_ip}:{object_name}"
    headers = [
        ("content-type", b"application/json"),
        ("schema-version", b"1.0"),
        ("source", b"report-tool-db-interface"),
        ("job-id", job_id.encode()),
        ("batch-seq", str(batch_seq).encode()),
        ("total-batches", str(total_batches).encode()),
        ("node-ip", node_ip.encode()),
        ("object-name", object_name.encode()),
        ("kpi-name", kpi_name.encode()),
        ("partition-key", partition_key.encode()),
        ("authorization", fake_token().encode()),
    ]
    return json.dumps(payload).encode(), headers, partition_key


def route_and_publish() -> None:
    """
    Minimal simulation of Report Tool gateway:
    1) estimates row_count
    2) applies light/heavy decision gate
    3) heavy path publishes one message per node-port-kpi
    """
    node_ports = [
        ("10.0.0.1", "PON-1/0/1"),
        ("10.0.0.2", "PON-1/0/2"),
        ("10.0.0.3", "PON-1/0/3"),
    ]
    kpis = ["octets_rx", "octets_tx", "errors_rx", "errors_tx"]
    rows_per_combo = 120
    force_heavy_demo = True

    combos = [(n, p, k) for (n, p) in node_ports for k in kpis]
    estimated_rows = len(combos) * rows_per_combo

    print(f"[RT] estimated_rows={estimated_rows}, threshold={ROW_COUNT_THRESHOLD}")
    if estimated_rows < ROW_COUNT_THRESHOLD and not force_heavy_demo:
        print("[RT] LIGHT PATH selected: would return HTTP 200 with inline data.")
        return

    job_id = f"JOB-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    total_batches = len(combos)
    print(
        f"[RT] HEAVY PATH selected: HTTP 202 Accepted. "
        f"job_id={job_id}, topic={TOPIC_INPUT}, total_batches={total_batches}"
    )

    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        acks="all",
        retries=3,
        value_serializer=None,
    )
    for idx, (node_ip, object_name, kpi_name) in enumerate(combos, start=1):
        body, headers, partition_key = build_batch(
            job_id=job_id,
            batch_seq=idx,
            total_batches=total_batches,
            node_ip=node_ip,
            object_name=object_name,
            kpi_name=kpi_name,
            points=rows_per_combo,
        )
        producer.send(
            TOPIC_INPUT,
            key=partition_key.encode(),
            value=body,
            headers=headers,
        )
    producer.flush()
    producer.close()
    print(f"[RT] Published {total_batches} messages to {TOPIC_INPUT}")


if __name__ == "__main__":
    route_and_publish()
